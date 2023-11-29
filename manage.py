from data_process import ReverseIndex
from database import MongoDB
from log_lg import ManageLog
from mongodb import del_repeat, find_all
from schedule import schedule


class Task:
    def __init__(self):
        ManageLog()

    @staticmethod
    def mongodb() -> None:
        with MongoDB() as db:
            del_repeat(db.col)

    @staticmethod
    def make_index() -> None:
        index = ReverseIndex()
        with MongoDB() as db:
            a = list(find_all(db.col))
        try:
            index.build_index(a)
            index.save_index()
        except AttributeError:
            pass


if __name__ == '__main__':
    task = Task()
    task1 = {
        'function': task.mongodb,
        'hour': 0,
        'minute': 0,
        'args': None
    }
    task2 = {
        'function': task.make_index,
        'hour': 0,
        'minute': 10,
        'args': None
    }
    schedule([task1, task2])
