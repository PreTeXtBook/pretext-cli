# Copyright (C) 2022 Steven Clontz and Oscar Levin

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pathlib import Path
from single_version import get_version
VERSION = get_version('pretextbook', Path(__file__).parent.parent)

CORE_COMMIT = "cdd5a5333a3332a48cae1e3289c4461520c7476e"
