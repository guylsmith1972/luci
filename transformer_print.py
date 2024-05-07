from uniparse import transform


class PrintTransformer:
    def __init__(self):
        self.level = 0
        
    def enter_class(self, node, context, body):
        print(f'{"   " * self.level}Entering class {context[-1]}: {".".join(context)}')
        self.level += 1
    
    def leave_class(self, node, context, body):
        self.level -= 1
        print(f'{"   " * self.level}Leaving class {context[-1]}: {".".join(context)}')
        
    def enter_function(self, node, context, body):
        print(f'{"   " * self.level}Entering function {context[-1]}: {".".join(context)}')
        print(body)
        self.level += 1

    def leave_function(self, node, context, body):
        self.level -= 1
        print(f'{"   " * self.level}Leaving function {context[-1]}: {".".join(context)}')
        
    def enter_other(self, node, context, body):
        print(f'{"   " * self.level}{node.type} -- {body}')
        self.level += 1

    def leave_other(self, node, context, body):
        self.level -= 1
        

def main():
    python_code = """
    class MyClass:
        def my_method(self, value):
            return value == 42

    def foo():
        pass
    """

    c_code = """
    class Foo {
    public:
        void (do_nothing) {}
    };
    
    int main(int argc, char**argv) {
        return 0
    }
    """

    transform(python_code, 'python', PrintTransformer())
    transform(c_code, 'cpp', PrintTransformer())


if __name__ == '__main__':
    main()
    