import sys
import json
import os
import datetime
import glob


class NikolaNotebook:
    def __init__(self, file_path):
        self.file_path = file_path
        self.notebook = self.load_ipynb()

    def load_ipynb(self):
        with open(self.file_path) as f:
            return json.load(f)

    def has_nikola_metadata(self):
        try:
            return 'nikola' in self.notebook['metadata']
        except:
            return False

    def append_default_metadata(self):
        name, _ = os.path.splitext(self.file_path)
        name = name.split('/')[-1]
        slug = name.replace(' ', '_')
        date = datetime.datetime.fromtimestamp(os.path.getctime(self.file_path))

        nikola_meta = {
            "title": name,
            "slug": slug,
            "date": date.strftime('%Y-%m-%d %H:%M:%S+09:00')
        }

        self.notebook['metadata'] = self.notebook.get('metadata', dict())
        self.notebook['metadata']['nikola'] = nikola_meta

    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.notebook, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':

    dir_path = os.path.abspath(sys.argv[1])
    dir_path = os.path.join(dir_path, '*.ipynb')
    for f in glob.glob(dir_path):
        try:
            book = NikolaNotebook(f)
            if not book.has_nikola_metadata():
                book.append_default_metadata()
                book.save()
        except:
            pass
