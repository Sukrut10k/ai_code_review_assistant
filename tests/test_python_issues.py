import os

def read_file(filename):
    f = open(filename, "r")
    data = f.read()
    return data   # file never closed (resource leak)

def divide(a, b):
    return a / b   # no zero check

def get_password():
    password = "admin123"   #  hardcoded secret (security issue)
    return password

def slow_function():
    result = []
    for i in range(100000):
        result.append(i)   # inefficient for large data
    return result

print(divide(10, 0))  # runtime crash
