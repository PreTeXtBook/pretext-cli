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

CORE_COMMIT = "3899672f474f0251ddec004ef31efd8bb5567153"
