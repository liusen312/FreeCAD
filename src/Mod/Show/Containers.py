#/***************************************************************************
# *   Copyright (c) Victor Titov (DeepSOIC)                                 *
# *                                           (vv.titov@gmail.com) 2018     *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This library is free software; you can redistribute it and/or         *
# *   modify it under the terms of the GNU Library General Public           *
# *   License as published by the Free Software Foundation; either          *
# *   version 2 of the License, or (at your option) any later version.      *
# *                                                                         *
# *   This library  is distributed in the hope that it will be useful,      *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this library; see the file COPYING.LIB. If not,    *
# *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
# *   Suite 330, Boston, MA  02111-1307, USA                                *
# *                                                                         *
# ***************************************************************************/

#This is a temporary replacement for C++-powered Container class that should be eventually introduced into FreeCAD

class Container(object):
    """Container class: a unified interface for container objects, such as Group, Part, Body, or Document.
    This is a temporary implementation"""
    Object = None #DocumentObject or Document, the actual container
    
    def __init__(self, obj):
        self.Object = obj
    
    def self_check(self):
        if self.Object is None:
            raise ValueError("Null!")
        if not isAContainer(self.Object):
            raise NotAContainerError(self.Object)
            
    def getAllChildren(self):
        return self.getStaticChildren() + self.getDynamicChildren()
    
    def getStaticChildren(self):
        self.self_check()
        container = self.Object
        
        if container.hasExtension("App::OriginGroupExtension"):
            if container.Origin is not None:
                return [container.Origin]
        elif container.isDerivedFrom("App::Origin"):
            return container.OriginFeatures

    def getDynamicChildren(self):
        self.self_check()
        container = self.Object
        
        if container.isDerivedFrom("App::Document"):
            # find all objects not contained by any Part or Body
            result = set(container.Objects)
            for obj in container.Objects:
                if isAContainer(obj):
                    children = set(getAllChildren(obj))
                    result = result - children
            return result
        elif container.hasExtension("App::GroupExtension"):
            result = container.Group
            if container.hasExtension('App::GeoFeatureGroupExtension'):
                #geofeaturegroup's group contains all objects within the CS, we don't want that
                result = [obj for obj in result if obj.getParentGroup() is not container]
            return result
        elif container.isDerivedFrom("App::Origin"):
            return []
        raise RuntimeError("getDynamicChildren: unexpected container type!")
    
    def isACS(self):
        """isACS(): returns true if the container forms internal coordinate system."""
        self.self_check()
        container = self.Object
        
        if container.isDerivedFrom("App::Document"):
            return True #Document is a special thing... is it a CS or not is a matter of coding convenience. 
        elif container.hasExtension("App::GeoFeatureGroupExtension"):
            return True
        else:
            return False
            
    def getCSChildren(self):
        if not self.isACS():
            raise TypeError("Container is not a coordinate system")
        container = self.Object

        if container.isDerivedFrom("App::Document"):
            result = set(container.Objects)
            for obj in container.Objects:
                if isAContainer(obj) and Container(obj).isACS():
                    children = set(Container(obj).getCSChildren())
                    result = result - children
            return result
        elif container.hasExtension('App::GeoFeatureGroupExtension'):
            return container.Group + self.getStaticChildren()
        else:
            assert(False)
    
    def hasObject(self, obj):
        return obj in self.getAllChildren()
            
def isAContainer(obj):
    '''isAContainer(obj): returns True if obj is an object container, such as 
    Group, Part, Body. The important characterisic of an object being a 
    container is that it can be activated to receive new objects. Documents 
    are considered containers, too.'''
    
    if obj.isDerivedFrom('App::Document'):
        return True
    if obj.hasExtension('App::GroupExtension'):
        return True
    if obj.isDerivedFrom('App::Origin'):
        return True
    return False

#from Part-o-magic...
def ContainerOf(obj):
    """ContainerOf(obj): returns the container that immediately has obj."""
    cnt = None
    for dep in obj.InList:
        if isAContainer(dep):
            if Container(dep).hasObject(obj):
                if cnt is not None and dep is not cnt:
                    raise ContainerTreeError("Container tree is not a tree")
                cnt = dep
    if cnt is None: 
        return obj.Document
    return cnt

#from Part-o-magic... over-engineered, but proven to work
def ContainerChain(feat):
    '''ContainerChain(feat): return a list of containers feat is in. 
    Last container directly contains the feature. 
    Example of output:  [<document>,<SuperPart>,<Part>,<Body>]'''
    
    if feat.isDerivedFrom('App::Document'):
        return []
    
    list_traversing_now = [feat]
    set_of_deps = set()
    list_of_deps = []
    
    while len(list_traversing_now) > 0:
        list_to_be_traversed_next = []
        for feat in list_traversing_now:
            for dep in feat.InList:
                if isAContainer(dep) and Container(dep).hasObject(feat):
                    if not (dep in set_of_deps):
                        set_of_deps.add(dep)
                        list_of_deps.append(dep)
                        list_to_be_traversed_next.append(dep)
        if len(list_to_be_traversed_next) > 1:
            raise ContainerTreeError("Container tree is not a tree")
        list_traversing_now = list_to_be_traversed_next
    
    return [feat.Document] + list_of_deps[::-1]

def CSChain(feat):
    cnt_chain = ContainerChain(feat)
    return [cnt for cnt in cnt_chain if Container(cnt).isACS()]


class ContainerError(RuntimeError):
    pass
class NotAContainerError(ContainerError):
    def __init__(self):
        ContainerError.__init__(self, u"{obj} is not recognized as container".format(obj.Name))
class ContainerTreeError(ContainerError):
    pass