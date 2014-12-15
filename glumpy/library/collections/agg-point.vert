// ----------------------------------------------------------------------------
// Copyright (c) 2014, Nicolas P. Rougier. All Rights Reserved.
// Distributed under the (new) BSD License.
// ----------------------------------------------------------------------------
// Hooks:
//  <transform> : vec4 function(position)
//
// ----------------------------------------------------------------------------
#version 120

// Externs
// ------------------------------------
// extern vec3 position;
// extern float size;
// extern vec4 color;

// Varyings
// ------------------------------------
varying float v_size;
varying vec4  v_color;


// Main (hooked)
// ------------------------------------
void main (void)
{
    fetch_uniforms();

    v_size = size;
    v_color = color;

    gl_Position = <transform(position)>;
    gl_PointSize = size + 2.0 * (1.0 + 1.5*1.0);
}
