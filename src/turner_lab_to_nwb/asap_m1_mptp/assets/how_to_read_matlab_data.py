from pathlib import Path
from pymatreader import read_mat

folder_path = Path("/home/heberto/data/turner/Ven_All")
assert folder_path.exists()

file_path = folder_path / "v1401.1.mat"
assert file_path.exists()

mat_file = read_mat(file_path)
