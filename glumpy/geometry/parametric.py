# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
import numpy as np
from . import normals
from glumpy import gloo



def surface(func):
    """
    Computes the parameterization of a parametric surface
    """

    vtype = [('position', np.float32, 3),
             ('texcoord', np.float32, 2),
             ('normal',   np.float32, 3)]
    itype = np.uint32

    umin, umax, ucount = 0, 2*np.pi, 48
    vmin, vmax, vcount = 0, 2*np.pi, 48
    vcount += 1
    ucount += 1
    n = vcount*ucount

    Un = np.repeat(np.linspace(0, 1, ucount, endpoint=True), vcount)
    Vn = np.tile  (np.linspace(0, 1, vcount, endpoint=True), ucount)
    U = umin+Un*(umax-umin)
    V = vmin+Vn*(vmax-vmin)

    vertices = np.zeros(n, dtype=vtype)
    for i,(u,v) in enumerate(zip(U,V)):
        vertices["position"][i] = func(u,v)

    vertices["texcoord"][:,0] = Un
    vertices["texcoord"][:,1] = Vn

    indices = []
    for i in range(ucount-1):
        for j in range(vcount-1):
            indices.append(i*(vcount) + j        )
            indices.append(i*(vcount) + j+1      )
            indices.append(i*(vcount) + j+vcount+1)
            indices.append(i*(vcount) + j+vcount  )
            indices.append(i*(vcount) + j+vcount+1)
            indices.append(i*(vcount) + j        )
    indices = np.array(indices, dtype=itype)
    vertices["normal"] = normals(vertices["position"],
                                 indices.reshape(len(indices)/3,3))

    return vertices.view(gloo.VertexBuffer), indices.view(gloo.IndexBuffer)