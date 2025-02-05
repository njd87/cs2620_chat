import tkinter as tk
from client import start_connection, service_connection

class ClientUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Messenger")
        self.root.geometry("400x400")

        self.setup_signup()

        self.root.mainloop()

    def setup_signup(self):
        main_label = tk.Label(self.root, text="Sign Up")

        username_label = tk.Label(self.root, text="Username")
        username_entry = tk.Entry(self.root)

        password_label = tk.Label(self.root, text="Password")
        password_entry = tk.Entry(self.root, show="*")

        signup_button = tk.Button(self.root, text="Sign Up", command=self.signup)

if __name__ == "__main__":
    root = tk.Tk()
    client_ui = ClientUI(root)