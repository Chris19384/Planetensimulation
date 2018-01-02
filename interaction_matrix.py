"""
helper class for interactive object motion
"""
#
# Copyright (C) 2007  "Peter Roesch" <Peter.Roesch@fh-augsburg.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# or open http://www.fsf.org/licensing/licenses/gpl.html

from __future__ import print_function
from __future__ import division

import sys

try:
    from OpenGL import GLUT
    from OpenGL import GL
except ImportError:
    print('Error: PyOpenGL not installed properly !!')
    sys.exit()

class InteractionMatrix:
    """Class holding a matrix representing a rigid transformation.

    The current OpenGL is read into an internal variable and
    updated using rotations and translations given by
    user interaction."""

    def __init__(self):
        self.__current_matrix = None
        self.reset()

    def reset(self):
        """Initialise internal matrix with identity"""
        GL.glPushMatrix()
        GL.glLoadIdentity()
        self.__current_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        GL.glPopMatrix()

    def add_translation(self, trans_x, trans_y, trans_z):
        """Concatenate the internal matrix with a translation matrix"""
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glTranslatef(trans_x, trans_y, trans_z)
        GL.glMultMatrixf(self.__current_matrix)
        self.__current_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        GL.glPopMatrix()

    def add_rotation(self, ang, rot_x, rot_y, rot_z):
        """Concatenate the internal matrix with a translation matrix"""
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glRotatef(ang, rot_x, rot_y, rot_z)
        GL.glMultMatrixf(self.__current_matrix)
        self.__current_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        GL.glPopMatrix()

    def get_current_matrix(self):
        """
            Get current transformation matrix resulting from interaction.
        """
        return self.__current_matrix

def _main(argv):
    GLUT.glutInit(argv)
    GLUT.glutCreateWindow(str.encode(sys.argv[0]))
    interaction_m = InteractionMatrix()
    print(interaction_m.get_current_matrix())
    interaction_m.add_translation(1, 2, 3)
    print(interaction_m.get_current_matrix())
    interaction_m.add_rotation(30, 0, 0, 1)
    print(interaction_m.get_current_matrix())
    interaction_m.add_translation(1, 2, 3)
    print(interaction_m.get_current_matrix())

if __name__ == '__main__':
    _main(sys.argv)
    