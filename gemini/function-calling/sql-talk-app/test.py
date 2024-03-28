# Testing OwlBot linting and checks

def my_function():
  if True:
   print("This is indented correctly")
    print("This is not")  # IndentationError

value = 10
# value is never used
print("Hello!")

data = requests.get("https://api.example.com")
