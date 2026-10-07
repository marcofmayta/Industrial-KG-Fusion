"""Keep machine-specific user paths out of published notebook outputs."""
import re
import nbformat

USER_PATH = re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\r\n:]*|/Users/[^\s:]+|/home/[^\s:]+')


def sanitize_outputs(notebook, root):
    def clean(value):
        if isinstance(value,str):
            value = value.replace(str(root),'<project>').replace(root.as_posix(),'<project>')
            return USER_PATH.sub('<local environment>',value)
        if isinstance(value,list):
            return [clean(item) for item in value]
        if isinstance(value,dict):
            return {key:clean(item) for key,item in value.items()}
        return value
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.outputs = [nbformat.from_dict(clean(output)) for output in cell.outputs]
    notebook.metadata = nbformat.from_dict(clean(notebook.metadata))
    return notebook
