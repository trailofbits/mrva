import os


directory = os.getenv("SOME_DIRECTORY")

path1 = f"{directory}/SOME_FILE1.txt"
fd1 = os.open(path1)
print(fd1.read())
fd1.close()

path2 = f"{directory}/SOME_FILE2.txt"
fd2 = os.open(path2)
print(fd2.read())
fd2.close()
