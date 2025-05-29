import os

def get_test_file(*parts):
    return os.path.join(os.path.dirname(__file__), "test_data", *parts)
