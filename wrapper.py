import importlib

def main():
    module = importlib.import_module('3dsconv.3dsconv')
    module.main()

if __name__ == '__main__':
    main()
