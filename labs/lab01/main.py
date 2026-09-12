"""Головний модуль запуску Лабораторної роботи №1."""

from labs.lab01.task1 import run_task1
from labs.lab01.task2 import run_task2
from labs.lab01.task3 import run_task3


def main():
    print("================ ЗАПУСК ЛАБОРАТОРНОЇ РОБОТИ №1 ================\n")
    run_task1()
    print("\n" + "=" * 63 + "\n")
    run_task2()
    print("\n" + "=" * 63 + "\n")
    run_task3()


if __name__ == "__main__":
    main()
