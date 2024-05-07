from uniparse import transform
import transformer


class PrintTransformer(transformer.Transformer):
    def __init__(self):
        super().__init__()
        self.level = 0
        
    def before_enter(self, args):
        super().before_enter(args)
        self.level += 1

    def after_leave(self, args):
        super().after_leave(args)
        self.level -= 1

    def enter_class(self, args):
        print(f'{"   " * self.level}Entering class {self.get_scope_name()}: {self.get_qualified_scope_name()}')
    
    def leave_class(self, args):
        print(f'{"   " * self.level}Leaving class {self.get_scope_name()}: {self.get_qualified_scope_name()}')
        
    def enter_function(self, args):
        print(f'{"   " * self.level}Entering function {self.get_scope_name()}: {self.get_qualified_scope_name()}')
        print(args["code_body"])

    def leave_function(self, args):
        print(f'{"   " * self.level}Leaving function {self.get_scope_name()}: {self.get_qualified_scope_name()}')
        
    def enter_other(self, args):
        print(f'{"   " * self.level}{args["node"].type} -- {args["code_body"]}')

        
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
    