# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier. All rights reserved.
# Distributed under the terms of the new BSD License.
# -----------------------------------------------------------------------------
import re
import numpy as np

from glumpy import gl
from glumpy.log import log
from . snippet import Snippet
from . globject import GLObject
from . buffer import VertexBuffer, IndexBuffer
from . shader import VertexShader, FragmentShader, GeometryShader
from . variable import gl_typeinfo, Uniform, Attribute



# ----------------------------------------------------------- Program class ---
class Program(GLObject):
    """
    A program is an object to which shaders can be attached and linked to create
    the program.
    """

    # ---------------------------------
    def __init__(self, verts=None, frags=None, geoms=None, count=0):
        """
        Initialize the program and register shaders to be linked.

        Parameters
        ----------

        verts : str, VertexShader, or list
            The vertex shader(s) to be used by this program

        frags : str, FragmentShader, or list
            The fragment shader(s) to be used by this program

        geoms : str, GeometryShader, or list
            The geometry shader(s) to be used by this program

        count : int (optional)
            Number of vertices this program will use. This can be given to
            initialize a VertexBuffer during Program initialization.

        Note
        ----

        If several vertex/fragment/geometry shaders are specified, only one can
        contain the main function respectively.
        """

        GLObject.__init__(self)
        self._count = count
        self._buffer = None

        # Make sure shaders are shaders
        self._verts = self._get_shaders(verts, VertexShader)
        self._frags = self._get_shaders(frags, FragmentShader)
        self._geoms = self._get_shaders(geoms, GeometryShader)

        self._uniforms = {}
        self._attributes = {}

        # Build hooks, uniforms and attributes
        self._build_hooks()
        self._build_uniforms()
        self._build_attributes()

        # Build associated structured vertex buffer if count is given
        if self._count > 0:
            dtype = []
            for attribute in self._attributes.values():
                dtype.append(attribute.dtype)
            self._buffer = np.zeros(self._count, dtype=dtype).view(VertexBuffer)
            self.bind(self._buffer)


    def _get_shaders(self, shaders, shader_class):

        # Get all geoms shaders
        if isinstance(shaders, (str, shader_class)):
            shaders = [shaders]
        elif isinstance(shaders, (type(None), tuple, list)):
            shaders = shaders or []
        else:
            raise ValueError('shaders must be str, Shader or list')

        # Apply
        shaders_list = []
        for shader in shaders:
            if isinstance(shader, str):
                shaders_list.append(shader_class(shader))
            elif isinstance(shader, shader_class):
                if shader not in shaders_list:
                    shaders_list.append(shader)
            else:
                raise ValueError('Cannot make a Shader out of %r.' % type(shader))

        return shaders_list


    def __len__(self):
        if self._buffer is not None:
            return len(self._buffer)
        else:
            return None


    # def attach(self, shaders):
    #     """ Attach one or several vertex/fragment shaders to the program.

    #     Parameters
    #     ----------

    #     shaders : VertexShader or FragmentShaders or list
    #         Shaders to attach
    #     """

    #     if isinstance(shaders, (VertexShader, FragmentShader)):
    #         shaders = [shaders]
    #     for shader in shaders:
    #         if isinstance(shader, VertexShader):
    #             self._verts.append(shader)
    #         elif isinstance(shader, FragmentShader):
    #             self._frags.append(shader)
    #         else:
    #             log.warn("Unknown shader type")

    #     # Ensure uniqueness of shaders
    #     self._verts = list(set(self._verts))
    #     self._frags = list(set(self._frags))

    #     self._need_create = True
    #     self._need_update = True

    #     # Build uniforms and attributes
    #     self._build_uniforms()
    #     self._build_attributes()



    def _setup(self):
        """ Setup the program by resolving all pending hooks. """
        pass


    # def detach(self, shaders):
    #     """Detach one or several vertex/fragment shaders from the program.

    #     Parameters
    #     ----------

    #     shaders : VertexShader or FragmentShaders or list
    #         Shaders to detach

    #     Note
    #     ----

    #     We don't need to defer attach/detach shaders since shader deletion
    #     takes care of that.
    #     """

    #     if type(shaders) in [VertexShader, FragmentShader]:
    #         shaders = [shaders]
    #     for shader in shaders:
    #         if isinstance(shader, VertexShader):
    #             if shader in self._verts:
    #                 self._verts.remove(shader)
    #             else:
    #                 raise ValueError("Shader is not attached to the program")
    #         elif isinstance(shader, FragmentShader):
    #             if shader in self._frags:
    #                 self._frags.remove(shader)
    #             else:
    #                 raise ValueError("Shader is not attached to the program")
    #     self._need_update = True

    #     # Build uniforms and attributes
    #     self._build_uniforms()
    #     self._build_attributes()


    def _create(self):
        """
        Build (link) the program and checks everything's ok.

        A GL context must be available to be able to build (link)
        """

        log.debug("GPU: Creating program")

        # Check if program has been created
        if self._handle <= 0:
            self._handle = gl.glCreateProgram()
            if not self._handle:
                raise ValueError("Cannot create program object")

        self._build_shaders(self._handle)

        log.debug("GPU: Linking program")

        # Link the program
        gl.glLinkProgram(self._handle)
        if not gl.glGetProgramiv(self._handle, gl.GL_LINK_STATUS):
            print(gl.glGetProgramInfoLog(self._handle))
            raise ValueError('Linking error')

        # Activate uniforms
        active_uniforms = [name for (name,gtype) in self.active_uniforms]
        for uniform in self._uniforms.values():
            if uniform.name in active_uniforms:
                uniform.active = True
            else:
                uniform.active = False

        # Activate attributes
        active_attributes = [name for (name,gtype) in self.active_attributes]
        for attribute in self._attributes.values():
            if attribute.name in active_attributes:
                attribute.active = True
            else:
                attribute.active = False


    def _build_shaders(self, program):
        """ Build and attach shaders """

        # Check if we have at least something to attach
        if not self._verts:
            raise ValueError("No vertex shader has been given")
        if not self._frags:
            raise ValueError("No fragment shader has been given")

        log.debug("GPU: Attaching shaders to program")

        # Attach shaders
        attached = gl.glGetAttachedShaders(program)
        shaders = self._verts + self._frags + self._geoms
        for shader in shaders: #self._verts:
            if shader.need_update:
                if shader.handle in attached:
                    gl.glDetachShader(program, handle)
                shader.activate()
                if isinstance(shader, GeometryShader):
                    if shader.vertices_out is not None:
                        gl.glProgramParameteriEXT(self._handle,
                                                  gl.GL_GEOMETRY_VERTICES_OUT_EXT,
                                                  shader.vertices_out)
                    if shader.input_type is not None:
                        gl.glProgramParameteriEXT(self._handle,
                                                  gl.GL_GEOMETRY_INPUT_TYPE_EXT,
                                                  shader.input_type)
                    if shader.output_type is not None:
                        gl.glProgramParameteriEXT(self._handle,
                                                  gl.GL_GEOMETRY_OUTPUT_TYPE_EXT,
                                                  shader.output_type)
                gl.glAttachShader(program, shader.handle)
                shader._program = self


    def _build_hooks(self):
        """ Build hooks """

        shaders = self._verts + self._frags + self._geoms
        self._hooks = {}
        for shader in shaders:
            for (hook,subhook) in shader.hooks:
                self._hooks[hook] = [shader, subhook, None]
        # for shader in shaders:
        #     for (hook,subhook) in shader.hooks:
        #         if hook in self._hooks.keys():
        #             if subhook not in self._hooks[hook][1]:
        #             self._hooks[hook][1].append(subhook)
        #         else:
        #             self._hooks[hook] = [shader, [subhook], None]



    def _build_uniforms(self):
        """ Build the uniform objects """

        # We might rebuild the program because of snippets but we must
        # keep already bound uniforms

        count = 0
        for (name,gtype) in self.all_uniforms:
            if name not in self._uniforms.keys():
                uniform = Uniform(self, name, gtype)
            else:
                uniform = self._uniforms[name]
            gtype = uniform.gtype
            if gtype in (gl.GL_SAMPLER_1D, gl.GL_SAMPLER_2D):
                uniform._texture_unit = count
                count += 1
            self._uniforms[name] = uniform
        self._need_update = True


    def _build_attributes(self):
        """ Build the attribute objects """

        # We might rebuild the program because of snippets but we must
        # keep already bound attributes

        dtype = []
        for (name,gtype) in self.all_attributes:
            if name not in self._attributes.keys():
                attribute = Attribute(self, name, gtype)
            else:
                attribute = self._attributes[name]

            self._attributes[name] = attribute
            dtype.append(attribute.dtype)


    def bind(self, data):
        """ """

        if isinstance(data, VertexBuffer):
            for name in data.dtype.names:
                if name in self._attributes.keys():
                    self._attributes[name].set_data(data.ravel()[name])


    def __setitem__(self, name, data):
        if name in self._hooks.keys():
            snippet = data
            shader = self._hooks[name][0]
            function = self._hooks[name][1]

            if isinstance(data, Snippet):
                snippet._default = function
            self._hooks[name][1] = snippet

            if function is not None:
                shader["%s.%s" %(name,function)] = snippet
            else:
                shader["%s" % (name)] = snippet

            if isinstance(data, Snippet):
                snippet.attach(self)
            self._build_uniforms()
            self._build_attributes()
            self._need_update = True

        elif name in self._uniforms.keys():
            self._uniforms[name].set_data(data)
        elif name in self._attributes.keys():
            self._attributes[name].set_data(data)
        else:
            raise IndexError("Unknown uniform or attribute")


    def __getitem__(self, name):
        if name in self._hooks.keys():
            return self._hooks[name][1]
        elif name in self._uniforms.keys():
            return self._uniforms[name].data
        elif name in self._attributes.keys():
            return self._attributes[name].data
        else:
            raise IndexError("Unknown uniform or attribute")


    def keys(self):
        """ Uniforme and attribute names """

        return self._uniforms.keys() + self._attributes.keys()


    def _activate(self):
        """Activate the program as part of current rendering state."""

        log.debug("GPU: Activating program (id=%d)" % self._id)
        gl.glUseProgram(self.handle)

        for uniform in self._uniforms.values():
            if uniform.active:
                uniform.activate()

        for attribute in self._attributes.values():
            if attribute.active:
                attribute.activate()


    def _deactivate(self):
        """Deactivate the program."""

        gl.glUseProgram(0)

        for uniform in self._uniforms.values():
            uniform.deactivate()
        for attribute in self._attributes.values():
            attribute.deactivate()
        log.debug("GPU: Deactivating program (id=%d)" % self._id)


    def _get_all_uniforms(self):
        """Extract uniforms from shaders code """

        uniforms = []
        for shader in self._verts:
            uniforms.extend(shader.uniforms)
        for shader in self._frags:
            uniforms.extend(shader.uniforms)
        for shader in self._geoms:
            uniforms.extend(shader.uniforms)
        uniforms = list(set(uniforms))
        return uniforms
    all_uniforms = property(_get_all_uniforms,
        doc = """ Program uniforms obtained from shaders code """)


    def _get_active_uniforms(self):
        """ Extract active uniforms from GPU """

        count = gl.glGetProgramiv(self.handle, gl.GL_ACTIVE_UNIFORMS)

        # This match a name of the form "name[size]" (= array)
        regex = re.compile("""(?P<name>\w+)\s*(\[(?P<size>\d+)\])\s*""")
        uniforms = []
        for i in range(count):
            name, size, gtype = gl.glGetActiveUniform(self.handle, i)
            # This checks if the uniform is an array
            # Name will be something like xxx[0] instead of xxx
            m = regex.match(name)
            # When uniform is an array, size corresponds to the highest used index
            if m:
                name = m.group('name')
                if size >= 1:
                    for i in range(size):
                        name = '%s[%d]' % (m.group('name'),i)
                        uniforms.append((name, gtype))
            else:
                uniforms.append((name, gtype))

        return uniforms
    active_uniforms = property(_get_active_uniforms,
        doc = "Program active uniforms obtained from GPU")



    def _get_inactive_uniforms(self):
        """ Extract inactive uniforms from GPU """

        active_uniforms = self.active_uniforms
        inactive_uniforms = self.all_uniforms
        for uniform in active_uniforms:
            if uniform in inactive_uniforms:
                inactive_uniforms.remove(uniform)
        return inactive_uniforms
    inactive_uniforms = property(_get_inactive_uniforms,
        doc = "Program inactive uniforms obtained from GPU")



    def _get_all_attributes(self):
        """ Extract attributes from shaders code """

        attributes= []
        for shader in self._verts:
            attributes.extend(shader.attributes)
        # No attribute in fragment shaders
        attributes = list(set(attributes))
        return attributes
    all_attributes = property(_get_all_attributes,
        doc = "Program attributes obtained from shaders code")



    def _get_active_attributes(self):
        """ Extract active attributes from GPU """

        count = gl.glGetProgramiv(self.handle, gl.GL_ACTIVE_ATTRIBUTES)
        attributes = []

        # This match a name of the form "name[size]" (= array)
        regex = re.compile("""(?P<name>\w+)\s*(\[(?P<size>\d+)\])""")

        for i in range(count):
            name, size, gtype = gl.glGetActiveAttrib(self.handle, i)

            # This checks if the attribute is an array
            # Name will be something like xxx[0] instead of xxx
            m = regex.match(name)
            # When attribute is an array, size corresponds to the highest used index
            if m:
                name = m.group('name')
                if size >= 1:
                    for i in range(size):
                        name = '%s[%d]' % (m.group('name'),i)
                        attributes.append((name, gtype))
            else:
                attributes.append((name, gtype))
        return attributes
    active_attributes = property(_get_active_attributes,
        doc = "Program active attributes obtained from GPU")



    def _get_inactive_attributes(self):
        """ Extract inactive attributes from GPU """

        active_attributes = self.active_attributes
        inactive_attributes = self.all_attributes
        for attribute in active_attributes:
            if attribute in inactive_attributes:
                inacative_attributes.remove(attribute)
        return inactive_attributes
    inactive_attributes = property(_get_inactive_attributes,
        doc = "Program inactive attributes obtained from GPU")


    @property
    def shaders(self):
        """ List of shaders currently attached to this program """

        shaders = []
        shaders.extend(self._verts)
        shaders.extend(self._frags)
        shaders.extend(self._geoms)
        return shaders



    def draw(self, mode = gl.GL_TRIANGLES, indices=None): #first=0, count=None):
        """ Draw the attribute arrays in the specified mode.

        Parameters
        ----------
        mode : GL_ENUM
            GL_POINTS, GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP,
            GL_TRIANGLES, GL_TRIANGLE_STRIP, GL_TRIANGLE_FAN

        first : int
            The starting vertex index in the vertex array. Default 0.

        count : int
            The number of vertices to draw. Default all.
        """

        self.activate()
        attributes = self._attributes.values()

        # Get buffer size first attribute
        # We need more tests here
        #  - do we have at least 1 attribute ?
        #  - does all attributes report same count ?
        # count = (count or attributes[0].size) - first

        if isinstance(indices, IndexBuffer):
            indices.activate()
            gltypes = { np.dtype(np.uint8) : gl.GL_UNSIGNED_BYTE,
                        np.dtype(np.uint16): gl.GL_UNSIGNED_SHORT,
                        np.dtype(np.uint32): gl.GL_UNSIGNED_INT }
            gl.glDrawElements(mode, indices.size, gltypes[indices.dtype], None)
            indices.deactivate()
        else:
            first = 0
            # count = (self._count or attributes[0].size) - first
            count = len(attributes[0])
            gl.glDrawArrays(mode, first, count)

        gl.glBindBuffer( gl.GL_ARRAY_BUFFER, 0 )
        self.deactivate()
