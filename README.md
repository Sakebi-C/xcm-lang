# XCM Programming Language

A simple, Python-like programming language that runs anywhere.

```python
# hello.xcm
say("Hello, World!")

var name = ask("What is your name? ")
say(f"Hello, {name}!")
```

---

## Installation

### Termux / Linux / macOS
```bash
curl -fsSL https://raw.githubusercontent.com/Sakebi-C/xcm-lang/main/install.sh | bash
```

### Windows
Download and run [`install.bat`](https://raw.githubusercontent.com/Sakebi-C/xcm-lang/main/install.bat)

---

## Usage

```bash
# Run a .xcm file
xcm run myfile.xcm

# Check version
xcm version
```

---

## Syntax

### Output & Input
```python
say("Hello!")               # print
say_red("Error!")           # colored output
say_green("Success!")
say_yellow("Warning!")
say_blue("Info!")
say_bold("Important!")
say_inline("Loading...")    # no newline

var name  = ask("Name: ")       # input string
var age   = ask_int("Age: ")    # input integer
var price = ask_float("Price: ")# input float
var pass  = ask_secret("Pass: ")# hidden input (shows ***)
```

### Variables
```python
var x     = 10
var name  = "Alex"
var score = 9.5
var found = True
var empty = maybe        # null/None

const MAX_HP = 100       # constant
var a, b, c = 1, 2, 3   # multiple assignment
```

### Operators
```python
# Arithmetic
x + y   x - y   x * y   x / y   x % y   x ** y   x // y

# Assignment
x += 1   x -= 1   x *= 2   x /= 2   x++   x--

# Comparison
==  !=  <  >  <=  >=

# Logic
and   or   not

# Null coalescing
var name = input_name ?? "Guest"

# Ternary
var label = "adult" if age >= 18 else "minor"
```

### Conditions
```python
if (x > 0):
    say("positive")
elif (x < 0):
    say("negative")
else:
    say("zero")

# Match / Case
match command:
    case "attack":
        say("You attack!")
    case "run":
        say("You run!")
    default:
        say("Unknown command.")
```

### Loops
```python
loop(5):              # repeat 5 times (i = 0..4)
    say(i)

repeat(3):            # repeat 3 times (no i variable)
    say("Hello!")

for i in range(10):   # 0 to 9
    say(i)

for i in range(1, 6): # 1 to 5
    say(i)

for item in myList:   # iterate list
    say(item)

while(x < 10):        # while loop
    x += 1

do:                   # do-while
    var x = ask_int("Enter positive number: ")
while(x <= 0):

break                 # exit loop
continue              # skip to next iteration
```

### Chance
```python
chance(50%):          # 50% probability
    say("Lucky!")

chance(1/6):          # 1 in 6 chance
    say("Rolled a 1!")
```

### Functions
```python
def greet(name, times = 1):
    loop(times):
        say(f"Hello, {name}!")

def add(a, b):
    return a + b

greet("Alex")
greet("World", 3)
say(add(10, 20))

# Lambda
var double = x => x * 2
say(double(5))        # 10
```

### Classes
```python
class Hero:
    def init(self, name, hp):
        self.name = name
        self.hp   = hp

    def attack(self):
        say(f"{self.name} attacks!")

    def heal(self, amount):
        self.hp += amount

var hero = new Hero("Alex", 100)
hero.attack()
hero.heal(20)
say(hero.hp)
```

### Enums
```python
enum Direction: UP, DOWN, LEFT, RIGHT
say(Direction.UP)     # 0
say(Direction.RIGHT)  # 3
```

### Lists
```python
var nums = [1, 2, 3, 4, 5]
nums.append(6)
nums.sort()
nums.reverse()
say(nums.first())     # first element
say(nums.last())      # last element
say(nums.size())      # length
say(nums.has(3))      # contains check
nums.remove(3)        # remove element

# Spread
var more = [0, ...nums, 9]

# Map / Filter / Reduce
var doubled = nums.map(x => x * 2)
var evens   = nums.filter(x => x % 2 == 0)
var total   = nums.reduce(0, (acc, x) => acc + x)
```

### Objects / Dictionaries
```python
var player = {name: "Alex", hp: 100, level: 1}
player.set("hp", 80)
say(player.get("name"))
say(player.keys())
say(player.values())
say(player.has_key("hp"))

# Object spread
var base   = {hp: 100, mp: 50}
var warrior = {...base, name: "Alex"}
```

### Strings
```python
var s = "Hello World"
say(s.upper())          # HELLO WORLD
say(s.lower())          # hello world
say(s.trim())           # trim whitespace
say(s.contains("World"))# True
say(s.split(" "))       # ["Hello", "World"]
say(s.replace("World", "XCM"))
say(s.size())           # 11
say("=" * 30)           # repeat string

# F-String
var name = "Alex"
say(f"Hello, {name}!")
say(f"Pi is {3.14159:.2f}")   # format number
say(f"Score: {1000:,}")       # 1,000

# Multi-line string
var text = """
Line one
Line two
"""
```

### Math
```python
round(3.7)      # 4
floor(3.9)      # 3
ceil(3.1)       # 4
abs(-5)         # 5
sqrt(16)        # 4.0
pow(2, 8)       # 256
random(1, 10)   # random int 1-10
random()        # random float 0-1
```

### Type Checking & Casting
```python
int("42")           # 42
float("3.14")       # 3.14
string(42)          # "42"

type_of(42)         # "number"
type_of("hi")       # "string"
type_of([])         # "list"
type_of({})         # "object"
type_of(maybe)      # "maybe"

is_number(42)       # True
is_string("hi")     # True
is_list([])         # True
is_object({})       # True

try_int("abc")      # maybe (safe parse)
try_float("abc")    # maybe (safe parse)

# is maybe check
if x is maybe:
    say("x is null")
if x is not maybe:
    say("x has value")

# Optional chaining
var name = player?.name ?? "Unknown"
```

### Error Handling
```python
try:
    var num = int("abc")
catch(err):
    say_error(f"Error: {err.message}")

# Throw
throw "Something went wrong!"

# Assert
assert hp > 0, "HP must be positive!"
```

### File I/O
```python
write_file("save.txt", "data")
append_file("save.txt", " more")
var content = read_file("save.txt")
say(file_exists("save.txt"))  # True
delete_file("save.txt")
```

### JSON
```python
var obj  = json_parse('{"name":"Alex"}')
var text = json_stringify(obj)
var pretty = json_stringify(obj, true)
```

### Timer & Date
```python
var t = start_timer()
wait(2s)
say(f"Elapsed: {stop_timer(t)}s")

var now = date_now()
say(f"{now.day}/{now.month}/{now.year}")
say(f"{now.hour}:{now.minute}:{now.second}")
```

### System
```python
clear()         # clear terminal
exit()          # exit program
exit(1)         # exit with code
beep()          # terminal bell

argv(0)         # CLI argument
env("HOME")     # environment variable
```

### Terminal UI
```python
progress_bar(75, 100)       # [===========>   ] 75%
print_table(
    ["Name", "ATK", "Rarity"],
    [["Alex", 100, "SSR"], ["Bob", 80, "SR"]]
)
```

### Import
```python
import "utils.xcm"
```

### Pipe Operator
```python
var result = "  hello  " |> trim() |> upper()
# HELLO
```

### Flags
Add at the top of your `.xcm` file:
```python
use wingui    # enable graphics features (window, draw_box, etc.)
use debug     # show transpiled output for debugging
```

---

## Examples

### Hello World
```python
say("Hello, World!")
```

### Calculator
```python
var a = ask_int("First number: ")
var b = ask_int("Second number: ")
say(f"{a} + {b} = {a + b}")
say(f"{a} - {b} = {a - b}")
say(f"{a} x {b} = {a * b}")
```

### Guess the Number
```python
const ANSWER = random(1, 100)
var tries = 0

say("Guess a number between 1 and 100!")

while(True):
    var guess = ask_int("Your guess: ")
    tries++

    if (guess < ANSWER):
        say_yellow("Too low!")
    elif (guess > ANSWER):
        say_yellow("Too high!")
    else:
        say_green(f"Correct! You got it in {tries} tries.")
        break
```

---

## License
MIT License — free to use, modify, and distribute.

## Author
[Sakebi-C](https://github.com/Sakebi-C)
