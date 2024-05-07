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
        """
        Returns a qualified scope name by joining the components with dots.

        This function takes no parameters and returns the qualified scope name, which is
        constructed by concatenating the individual components with dots.

        Parameters:
        self (object): The object instance of the class or module that contains this
                    method.

        Returns:
        string: The qualified scope name, constructed by joining the individual
                components with dots.

        Examples:
        Get the qualified scope name for a given object instance.   qualified_scope_name
         = get_qualified_scope_name(self)
        """
        return '.'.join(filter(None, self.qualified_scope_name))

    def get_scope_name(self):
        """
        Returns the name of the current scope.

        This function returns the name of the current scope. It prints the qualified
        scope name and then reduces it to get the last part, which represents the scope
        name.

        Parameters:
        self (object): The object instance for which this method is called.

        Returns:
        string | None: The name of the current scope, or None if it's not available.

        Examples:
        Get the name of the current scope.   scope_name = get_scope_name()
        """
        print(self.qualified_scope_name)
        reduced = filter(None, self.qualified_scope_name)
        return reduced[-1] if reduced else None    
    