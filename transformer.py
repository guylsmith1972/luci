class Transformer:
    def __init__(self):
        self.qualified_scope_name = []
        
    def before_enter(self, args):
        self.qualified_scope_name.append(args['name'])

    def after_enter(self, args):
        pass
        
    def before_leave(self, args):
        pass
    
    def after_leave(self, args):
        self.qualified_scope_name.pop()
        
    def enter_class(self, args):
        pass
    
    def leave_class(self, args):
        pass
        
    def enter_function(self, args):
        pass

    def leave_function(self, args):
        pass
        
    def enter_other(self, args):
        pass

    def leave_other(self, args):
        pass
    
    def get_qualified_scope_name(self):
        return '.'.join(filter(None, self.qualified_scope_name))
