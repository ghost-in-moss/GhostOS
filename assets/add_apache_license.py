import os
import sys
import re

def add_license_header(directory, author_name, year):
    # 使用传入的年份和作者名更新版权声明
    header = f'''# Copyright {year} by {author_name}
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''

    # visit .py files recursively and replace-write the license header
    for subdir, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(subdir, file)
            if filepath.endswith(".py"):
                with open(filepath, 'r+') as f:
                    content = f.read()
                    # 查找并替换旧的版权和许可证声明
                    new_content = re.sub(r'# Copyright \d{4} by .+\n#\n# Licensed under the Apache License, Version 2.0 .+\n# you may not use .+\n# See the License for the specific language governing permissions and\n# limitations under the License.\n\n',
                                         '', content, flags=re.DOTALL)
                    f.seek(0, 0)
                    f.write(header.rstrip('\r\n') + '\n\n' + new_content)
                    f.truncate()  # Truncate the file to the current position


# usage example:
# python add_apache_license.py <directory> <name of authors or organization> <year>
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <directory> <author_name> <year>")
        sys.exit(1)
    directory = sys.argv[1]
    author_name = sys.argv[2]
    year = sys.argv[3]
    add_license_header(directory, author_name, year)
