from werkzeug.security import check_password_hash

class User:
    def __init__(self,username,name,dp_url):
        self.username = username
        self.name = name
        self.dp_url = dp_url

    @staticmethod
    def is_authenticated(self):
        return True
    
    @staticmethod
    def is_active(self):
        return True
    
    @staticmethod
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return self.username
    
    def check_password(self,password_input):
        return True
