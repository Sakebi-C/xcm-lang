#!/usr/bin/env python3
# ============================================================
#  XCM Language Engine
#  Version : 1.0.0
#  Pure Python Interpreter — no Node.js required
# ============================================================

import sys
import os
import re
import math
import json
import random
import time
def _ask_secret_impl(prompt):
    print(prompt, end="", flush=True)
    result = ""
    if os.name == "nt":
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch in ('\r', '\n'):
                break
            elif ch == '\x08':
                if result:
                    result = result[:-1]
                    print('\x08 \x08', end="", flush=True)
            elif ch == '\x03':
                raise KeyboardInterrupt
            else:
                result += ch
                print("*", end="", flush=True)
    else:
        import tty, termios
        fd  = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    break
                elif ch == '\x7f':
                    if result:
                        result = result[:-1]
                        print('\x08 \x08', end="", flush=True)
                elif ch == '\x03':
                    raise KeyboardInterrupt
                else:
                    result += ch
                    print("*", end="", flush=True)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    print()
    return result

    def __init__(self, message, line=None, source=None):
        self.message = message
        self.line    = line
        self.source  = source
        super().__init__(message)
    def __str__(self):
        if self.line is not None:
            base = f"XCM Error on line {self.line}: {self.message}"
            if self.source:
                base += f"\n    |  {self.source}\n    |  ^"
            return base
        return f"XCM Error: {self.message}"

class XCMObject(dict):
    def __getattr__(self, key):
        try:    return self[key]
        except: raise XCMError(f"Object has no attribute '{key}'")
    def __setattr__(self, key, value): self[key] = value
    def __repr__(self):
        return "{" + ", ".join(f"{k}: {xcm_repr(v)}" for k, v in self.items()) + "}"

class XCMEnum:
    def __init__(self, name, values):
        self.name = name
        for i, v in enumerate(values):
            object.__setattr__(self, v, i)
    def __repr__(self): return f"<Enum {self.name}>"

class XCMFunction:
    def __init__(self, name, params, body_lines, closure_env):
        self.name        = name
        self.params      = params
        self.body_lines  = body_lines
        self.closure_env = closure_env
    def __repr__(self): return f"<function {self.name}>"

class XCMClass:
    def __init__(self, name, methods, parent=None):
        self.name        = name
        self.methods     = methods
        self.parent      = parent
        self.closure_env = None
    def __repr__(self): return f"<class {self.name}>"

class XCMInstance:
    def __init__(self, xcm_class):
        object.__setattr__(self, '_class',  xcm_class)
        object.__setattr__(self, '_fields', {})
    def __getattr__(self, key):
        if key.startswith('_'): return object.__getattribute__(self, key)
        fields = object.__getattribute__(self, '_fields')
        if key in fields: return fields[key]
        cls = object.__getattribute__(self, '_class')
        while cls:
            if key in cls.methods:
                return BoundMethod(cls.methods[key], self)
            cls = cls.parent
        raise XCMError(f"'{object.__getattribute__(self, '_class').name}' has no attribute '{key}'")
    def __setattr__(self, key, value):
        if key.startswith('_'): object.__setattr__(self, key, value)
        else: object.__getattribute__(self, '_fields')[key] = value
    def __repr__(self):
        cls    = object.__getattribute__(self, '_class')
        fields = object.__getattribute__(self, '_fields')
        return f"<{cls.name} {fields}>"

class BoundMethod:
    def __init__(self, func, instance):
        self.func     = func
        self.instance = instance
    def __call__(self, *args): return self.func(self.instance, *args)
    def __repr__(self): return f"<bound method>"

class XCMLambda:
    """Standalone lambda: var double = x => x * 2"""
    def __init__(self, params, body, closure_env):
        self.params      = params
        self.body        = body
        self.closure_env = closure_env
    def __call__(self, *args):
        local_env = Environment(self.closure_env)
        for i, p in enumerate(self.params):
            local_env.set(p, args[i] if i < len(args) else None)
        return eval_expr(self.body, local_env)
    def __repr__(self): return f"<lambda>"

class ReturnException(Exception):
    def __init__(self, value): self.value = value
class BreakException(Exception):    pass
class ContinueException(Exception): pass

# ============================================================
#  HELPERS
# ============================================================

def xcm_repr(val):
    if val is None:    return "maybe"
    if val is True:    return "True"
    if val is False:   return "False"
    if isinstance(val, float) and val == int(val): return str(int(val))
    if isinstance(val, list):  return "[" + ", ".join(xcm_repr(v) for v in val) + "]"
    return str(val)

def xcm_str(val):
    if val is None:    return "maybe"
    if val is True:    return "True"
    if val is False:   return "False"
    if isinstance(val, float) and val == int(val): return str(int(val))
    if isinstance(val, list):  return "[" + ", ".join(xcm_repr(v) for v in val) + "]"
    return str(val)

def xcm_bool(val):
    """Python truthiness for XCM values."""
    if val is None:  return False
    if val is False: return False
    if val == 0 or val == 0.0: return False
    if val == "":    return False
    if isinstance(val, list) and len(val) == 0: return False
    if isinstance(val, dict) and len(val) == 0: return False
    return True

def unescape(s):
    return (s.replace('\\n', '\n')
             .replace('\\t', '\t')
             .replace('\\r', '\r')
             .replace('\\"', '"')
             .replace("\\'", "'")
             .replace('\\\\', '\\'))

# ============================================================
#  ENVIRONMENT
# ============================================================

class Environment:
    def __init__(self, parent=None):
        self.vars   = {}
        self.parent = parent
    def get(self, name):
        if name in self.vars: return self.vars[name]
        if self.parent: return self.parent.get(name)
        raise XCMError(f"Undefined variable '{name}'")
    def set(self, name, value): self.vars[name] = value
    def assign(self, name, value):
        if name in self.vars: self.vars[name] = value
        elif self.parent: self.parent.assign(name, value)
        else: self.vars[name] = value
    def has(self, name):
        if name in self.vars: return True
        if self.parent: return self.parent.has(name)
        return False

# ============================================================
#  SPLIT HELPERS
# ============================================================

def split_outside(expr, sep, skip_unary=False):
    parts  = []
    depth  = 0
    in_str = None
    cur    = ''
    i      = 0
    slen   = len(sep)
    while i < len(expr):
        ch = expr[i]
        if in_str:
            cur += ch
            if ch == in_str and (i == 0 or expr[i-1] != '\\'): in_str = None
        elif ch in ('"', "'"):
            in_str = ch; cur += ch
        elif ch in ('(', '[', '{'): depth += 1; cur += ch
        elif ch in (')', ']', '}'): depth -= 1; cur += ch
        elif depth == 0 and expr[i:i+slen] == sep:
            if skip_unary and not cur.strip(): cur += ch; i += 1; continue
            parts.append(cur); cur = ''; i += slen; continue
        else: cur += ch
        i += 1
    parts.append(cur)
    return parts if len(parts) > 1 else [expr]

def split_args(expr):
    return split_outside(expr, ',') if expr.strip() else []

def matching_close(s, open_pos):
    open_ch  = s[open_pos]
    close_ch = {'(':')', '[':']', '{':'}'}[open_ch]
    depth = 0
    for i in range(open_pos, len(s)):
        if s[i] == open_ch:  depth += 1
        if s[i] == close_ch: depth -= 1
        if depth == 0: return i
    return -1

def split_ternary(expr):
    if ' if ' not in expr or ' else ' not in expr: return None
    depth = 0; in_str = None
    for i, ch in enumerate(expr):
        if in_str:
            if ch == in_str: in_str = None
        elif ch in ('"', "'"): in_str = ch
        elif ch in ('(','[','{'): depth += 1
        elif ch in (')',']','}'): depth -= 1
        elif depth == 0:
            if expr[i:i+4] == ' if ':
                left = expr[:i].strip()
                rest = expr[i+4:]
                if ' else ' in rest:
                    mid, right = rest.split(' else ', 1)
                    return left, mid.strip(), right.strip()
    return None

# ============================================================
#  EXPRESSION EVALUATOR
# ============================================================

def eval_expr(expr, env, line_num=None):
    expr = expr.strip()
    if not expr: return None

    # Literals
    if expr == 'maybe': return None
    if expr == 'True':  return True
    if expr == 'False': return False

    # Lambda: x => expr  or  (x, y) => expr
    lm = re.match(r'^\(?([\w,\s]+)\)?\s*=>\s*(.+)$', expr)
    if lm and '=>' in expr:
        params = [p.strip() for p in lm.group(1).split(',')]
        body   = lm.group(2).strip()
        return XCMLambda(params, body, env)

    # Null coalescing: a ?? b
    parts = split_outside(expr, '??')
    if len(parts) == 2:
        left = eval_expr(parts[0].strip(), env, line_num)
        return left if left is not None else eval_expr(parts[1].strip(), env, line_num)

    # Optional chaining: obj?.attr or obj?.method()
    if '?.' in expr:
        m = re.match(r'^(.+?)\?\.([\w]+)(?:\((.*)\))?$', expr)
        if m:
            obj = eval_expr(m.group(1).strip(), env, line_num)
            if obj is None: return None
            attr = m.group(2)
            if m.group(3) is not None:
                args_str = m.group(3).strip()
                args = [eval_expr(a.strip(), env, line_num) for a in split_args(args_str)] if args_str else []
                return call_builtin_method(obj, attr, args, env, line_num)
            return eval_dotchain(f"__tmp__.{attr}", type('E', (), {'has': lambda s,x: True, 'get': lambda s,x: obj, 'vars': {'__tmp__': obj}, 'parent': env})(), line_num)

    # Pipe: a |> fn()
    parts = split_outside(expr, '|>')
    if len(parts) > 1:
        val = eval_expr(parts[0].strip(), env, line_num)
        for part in parts[1:]:
            fn_name = part.strip().rstrip('()')
            val = call_builtin_method(val, fn_name, [], env, line_num)
        return val

    # Ternary: A if cond else B
    t = split_ternary(expr)
    if t:
        val_true, cond, val_false = t
        return eval_expr(val_true, env, line_num) if xcm_bool(eval_expr(cond, env, line_num)) else eval_expr(val_false, env, line_num)

    # or
    parts = split_outside(expr, ' or ')
    if len(parts) > 1:
        for p in parts:
            v = eval_expr(p.strip(), env, line_num)
            if xcm_bool(v): return v
        return v

    # and
    parts = split_outside(expr, ' and ')
    if len(parts) > 1:
        v = None
        for p in parts:
            v = eval_expr(p.strip(), env, line_num)
            if not xcm_bool(v): return v
        return v

    # not
    if expr.startswith('not '):
        return not xcm_bool(eval_expr(expr[4:].strip(), env, line_num))

    # is maybe / is not maybe
    m = re.match(r'^(.+)\s+is\s+not\s+maybe$', expr)
    if m: return eval_expr(m.group(1).strip(), env, line_num) is not None
    m = re.match(r'^(.+)\s+is\s+maybe$', expr)
    if m: return eval_expr(m.group(1).strip(), env, line_num) is None

    # Chained comparison: 0 < x < 10
    chain = re.match(r'^(.+?)\s*(<|>|<=|>=)\s*(.+?)\s*(<|>|<=|>=)\s*(.+)$', expr)
    if chain:
        try:
            a   = eval_expr(chain.group(1), env, line_num)
            op1 = chain.group(2)
            b   = eval_expr(chain.group(3), env, line_num)
            op2 = chain.group(4)
            c   = eval_expr(chain.group(5), env, line_num)
            def cmp(x, op, y):
                if op == '<':  return x < y
                if op == '>':  return x > y
                if op == '<=': return x <= y
                if op == '>=': return x >= y
            return cmp(a, op1, b) and cmp(b, op2, c)
        except: pass

    # Comparisons
    for op in ['==', '!=', '<=', '>=', '<', '>']:
        parts = split_outside(expr, op)
        if len(parts) == 2:
            l = eval_expr(parts[0].strip(), env, line_num)
            r = eval_expr(parts[1].strip(), env, line_num)
            if op == '==': return l == r
            if op == '!=': return l != r
            if op == '<=': return (l or 0) <= (r or 0)
            if op == '>=': return (l or 0) >= (r or 0)
            if op == '<':  return (l or 0) <  (r or 0)
            if op == '>':  return (l or 0) >  (r or 0)

    # Addition / subtraction
    parts = split_outside(expr, '+')
    if len(parts) > 1:
        result = eval_expr(parts[0].strip(), env, line_num)
        for p in parts[1:]:
            r = eval_expr(p.strip(), env, line_num)
            if isinstance(result, str) or isinstance(r, str):
                result = xcm_str(result) + xcm_str(r)
            else:
                result = (result or 0) + (r or 0)
        return result

    parts = split_outside(expr, '-', skip_unary=True)
    if len(parts) > 1:
        result = eval_expr(parts[0].strip(), env, line_num)
        for p in parts[1:]:
            result = (result or 0) - (eval_expr(p.strip(), env, line_num) or 0)
        return result

    # Power
    parts = split_outside(expr, '**')
    if len(parts) == 2:
        return eval_expr(parts[0].strip(), env, line_num) ** eval_expr(parts[1].strip(), env, line_num)

    # Multiply
    parts = split_outside(expr, '*')
    if len(parts) > 1:
        l = eval_expr(parts[0].strip(), env, line_num)
        r = eval_expr(parts[1].strip(), env, line_num)
        if isinstance(l, str): return l * int(r)
        if isinstance(r, str): return r * int(l)
        result = (l or 0) * (r or 0)
        for p in parts[2:]:
            result *= (eval_expr(p.strip(), env, line_num) or 0)
        return result

    # Floor div / divide / modulo
    parts = split_outside(expr, '//')
    if len(parts) == 2:
        return int((eval_expr(parts[0].strip(), env, line_num) or 0) // (eval_expr(parts[1].strip(), env, line_num) or 1))

    parts = split_outside(expr, '/')
    if len(parts) == 2:
        r = eval_expr(parts[1].strip(), env, line_num) or 0
        if r == 0: raise XCMError("Division by zero", line_num)
        return (eval_expr(parts[0].strip(), env, line_num) or 0) / r

    parts = split_outside(expr, '%')
    if len(parts) == 2:
        return (eval_expr(parts[0].strip(), env, line_num) or 0) % (eval_expr(parts[1].strip(), env, line_num) or 1)

    # Unary minus
    if expr.startswith('-') and len(expr) > 1:
        try: return -eval_expr(expr[1:].strip(), env, line_num)
        except: pass

    # Parentheses
    if expr.startswith('(') and expr.endswith(')') and matching_close(expr, 0) == len(expr)-1:
        return eval_expr(expr[1:-1], env, line_num)

    # List literal
    if expr.startswith('[') and expr.endswith(']'):
        inner = expr[1:-1].strip()
        if not inner: return []
        result = []
        for item in split_args(inner):
            item = item.strip()
            if item.startswith('...'):
                val = eval_expr(item[3:], env, line_num)
                result.extend(val if isinstance(val, list) else [])
            else:
                result.append(eval_expr(item, env, line_num))
        return result

    # Object literal
    if expr.startswith('{') and expr.endswith('}'):
        inner = expr[1:-1].strip()
        if not inner: return XCMObject()
        obj   = XCMObject()
        pairs = split_args(inner)
        for pair in pairs:
            pair = pair.strip()
            if pair.startswith('...'):
                # object spread: {...base}
                src = eval_expr(pair[3:], env, line_num)
                if isinstance(src, dict):
                    obj.update(src)
            elif ':' in pair:
                k, v = pair.split(':', 1)
                obj[k.strip().strip('"').strip("'")] = eval_expr(v.strip(), env, line_num)
        return obj

    # Multi-line string: """..."""
    if expr.startswith('"""') and expr.endswith('"""'):
        return unescape(expr[3:-3])

    # String literals
    if (expr.startswith('"') and expr.endswith('"')) or \
       (expr.startswith("'") and expr.endswith("'")):
        return unescape(expr[1:-1])

    # F-string with format spec: f"{val:.2f}" f"{val:,}" f"{val:05d}"
    if (expr.startswith('f"') and expr.endswith('"')) or \
       (expr.startswith("f'") and expr.endswith("'")):
        inner = expr[2:-1]
        def replace_interp(m):
            content = m.group(1)
            if ':' in content:
                varpart, fmt = content.split(':', 1)
                val = eval_expr(varpart.strip(), env, line_num)
                try:
                    return format(val, fmt)
                except:
                    return xcm_str(val)
            return xcm_str(eval_expr(content, env, line_num))
        return unescape(re.sub(r'\{([^}]+)\}', replace_interp, inner))

    # Multi-line f-string: f"""..."""
    if (expr.startswith('f"""') and expr.endswith('"""')):
        inner = expr[4:-3]
        def replace_interp_ml(m):
            content = m.group(1)
            if ':' in content:
                varpart, fmt = content.split(':', 1)
                val = eval_expr(varpart.strip(), env, line_num)
                try: return format(val, fmt)
                except: return xcm_str(val)
            return xcm_str(eval_expr(content, env, line_num))
        return unescape(re.sub(r'\{([^}]+)\}', replace_interp_ml, inner))

    # Method chain / attribute access
    if '.' in expr and not expr.startswith('.'):
        result = eval_dotchain(expr, env, line_num)
        if result is not None: return result

    # Function call
    m = re.match(r'^(\w+)\s*\((.*)\)$', expr, re.DOTALL)
    if m:
        fn_name  = m.group(1)
        args_str = m.group(2).strip()
        args = [eval_expr(a.strip(), env, line_num) for a in split_args(args_str)] if args_str else []
        return call_function(fn_name, args, env, line_num)

    # Index access: expr[index]
    m = re.match(r'^(.+)\[(.+)\]$', expr)
    if m:
        obj = eval_expr(m.group(1).strip(), env, line_num)
        idx = eval_expr(m.group(2).strip(), env, line_num)
        if isinstance(obj, (list, str)):
            return obj[int(idx)]
        if isinstance(obj, dict):
            return obj.get(str(idx))

    # Number literals
    try:
        if '.' in expr: return float(expr)
        return int(expr)
    except (ValueError, TypeError): pass

    # Variable
    if re.match(r'^\w+$', expr):
        return env.get(expr)

    return None

def _parse_method_call(rest):
    """Parse method_name(args)remainder safely, respecting nested parens/strings."""
    m = re.match(r'^(\w+)\s*\(', rest)
    if not m:
        return None
    method_name = m.group(1)
    start = len(m.group(0)) - 1  # position of opening (
    close = matching_close(rest, start)
    if close == -1:
        return None
    args_str  = rest[start+1:close]
    remainder = rest[close+1:].strip()
    return method_name, args_str, remainder

def eval_dotchain(expr, env, line_num=None):
    depth = 0; in_str = None
    for i, ch in enumerate(expr):
        if in_str:
            if ch == in_str: in_str = None
        elif ch in ('"', "\'"): in_str = ch
        elif ch in ('(', '[', '{'): depth += 1
        elif ch in (')', ']', '}'): depth -= 1
        elif ch == '.' and depth == 0 and i > 0:
            obj_expr = expr[:i]
            rest     = expr[i+1:]
            try:
                obj = eval_expr(obj_expr, env, line_num)
            except: return None

            # Method call — use safe parser
            parsed = _parse_method_call(rest)
            if parsed:
                method_name, args_str, remainder = parsed
                args = [eval_expr(a.strip(), env, line_num) for a in split_args(args_str)] if args_str.strip() else []
                result = call_builtin_method(obj, method_name, args, env, line_num)
                if remainder.startswith('.'):
                    tmp_env = Environment(env)
                    tmp_env.set('__tmp__', result)
                    return eval_dotchain('__tmp__' + remainder, tmp_env, line_num)
                return result

            # Nested attribute chain
            if '.' in rest:
                tmp_env = Environment(env)
                tmp_env.set('__tmp__', obj)
                return eval_dotchain('__tmp__.' + rest, tmp_env, line_num)

            # Single attribute
            attr = rest.strip()
            if attr == 'length': return len(obj) if obj is not None else 0
            if isinstance(obj, (XCMObject, dict)): return obj.get(attr)
            if isinstance(obj, XCMInstance):        return getattr(obj, attr)
            if isinstance(obj, XCMEnum):            return getattr(obj, attr, None)
            return getattr(obj, attr, None)
    return None

def call_builtin_method(obj, method, args, env, line_num=None):
    # String methods
    if isinstance(obj, str):
        if method == 'upper':      return obj.upper()
        if method == 'lower':      return obj.lower()
        if method == 'trim':       return obj.strip()
        if method == 'contains':   return (args[0] in obj) if args else False
        if method == 'split':      return obj.split(args[0]) if args else list(obj)
        if method == 'replace':    return obj.replace(args[0], args[1]) if len(args)>=2 else obj
        if method == 'pad':        return obj.rjust(int(args[0])) if args else obj
        if method == 'matches':    return bool(re.search(str(args[0]), obj)) if args else False
        if method == 'startswith': return obj.startswith(args[0]) if args else False
        if method == 'endswith':   return obj.endswith(args[0]) if args else False
        if method == 'repeat':     return obj * int(args[0]) if args else obj
        if method == 'size':       return len(obj)
        if method == 'format':     return format(obj, args[0]) if args else obj
        if method == 'index':      return obj.index(args[0]) if args else -1

    # List methods
    if isinstance(obj, list):
        if method == 'append':  obj.append(args[0] if args else None); return None
        if method == 'push':    obj.append(args[0] if args else None); return None
        if method == 'pop':     return obj.pop() if obj else None
        if method == 'sort':    obj.sort(key=lambda x: (0 if isinstance(x,(int,float)) else 1, x) if not isinstance(x, dict) else (1, str(x))); return None
        if method == 'reverse': obj.reverse(); return None
        if method == 'first':   return obj[0]  if obj else None
        if method == 'last':    return obj[-1] if obj else None
        if method == 'has':     return (args[0] in obj) if args else False
        if method == 'size':    return len(obj)
        if method == 'remove':
            if args and args[0] in obj: obj.remove(args[0])
            return None
        if method == 'join':
            sep = xcm_str(args[0]) if args else ''
            return sep.join(xcm_str(x) for x in obj)
        if method == 'index':   return obj.index(args[0]) if args and args[0] in obj else -1
        if method == 'slice':
            s = int(args[0]) if args else 0
            e = int(args[1]) if len(args) > 1 else len(obj)
            return obj[s:e]
        if method == 'map':
            fn = args[0] if args else None
            return [call_xcm_callable(fn, [item], env, line_num) for item in obj]
        if method == 'filter':
            fn = args[0] if args else None
            return [item for item in obj if xcm_bool(call_xcm_callable(fn, [item], env, line_num))]
        if method == 'reduce':
            fn  = args[1] if len(args) > 1 else (args[0] if args else None)
            acc = args[0] if len(args) > 1 else (obj[0] if obj else None)
            items = obj if len(args) > 1 else obj[1:]
            for item in items:
                acc = call_xcm_callable(fn, [acc, item], env, line_num)
            return acc

    # Object/dict methods
    if isinstance(obj, dict):
        if method == 'get':     return obj.get(str(args[0])) if args else None
        if method == 'set':
            if len(args) >= 2: obj[str(args[0])] = args[1]
            return None
        if method == 'keys':    return list(obj.keys())
        if method == 'values':  return list(obj.values())
        if method == 'has_key': return (str(args[0]) in obj) if args else False

    # Instance methods
    if isinstance(obj, XCMInstance):
        attr = getattr(obj, method, None)
        if attr is not None:
            if callable(attr): return attr(*args)
            return attr

    if isinstance(obj, BoundMethod): return obj(*args)
    if isinstance(obj, XCMLambda):   return obj(*args)

    return None

def call_xcm_callable(fn, args, env, line_num=None):
    if isinstance(fn, XCMLambda):   return fn(*args)
    if isinstance(fn, XCMFunction):
        local_env = Environment(fn.closure_env)
        for i, (pname, pdefault) in enumerate(fn.params):
            local_env.set(pname, args[i] if i < len(args) else pdefault)
        interp = Interpreter()
        interp.global_env = fn.closure_env
        try:
            interp.execute_block(fn.body_lines, local_env)
        except ReturnException as r: return r.value
        return None
    if isinstance(fn, str):
        lm = re.match(r'^\(?([\w,\s]+)\)?\s*=>\s*(.+)$', fn.strip())
        if lm:
            params = [p.strip() for p in lm.group(1).split(',')]
            body   = lm.group(2).strip()
            local_env = Environment(env)
            for i, p in enumerate(params):
                local_env.set(p, args[i] if i < len(args) else None)
            return eval_expr(body, local_env, line_num)
    if callable(fn): return fn(*args)
    return None

def call_function(name, args, env, line_num=None):
    # User-defined / lambda variable
    if env.has(name):
        fn = env.get(name)
        if isinstance(fn, XCMLambda):   return fn(*args)
        if isinstance(fn, XCMFunction):
            local_env = Environment(fn.closure_env)
            for i, (pname, pdefault) in enumerate(fn.params):
                local_env.set(pname, args[i] if i < len(args) else pdefault)
            interp = Interpreter()
            interp.global_env  = fn.closure_env
            interp.xcm_globals = {}
            try:
                interp.execute_block(fn.body_lines, local_env)
            except ReturnException as r: return r.value
            return None
        if isinstance(fn, XCMClass):
            inst = XCMInstance(fn)
            if 'init' in fn.methods: fn.methods['init'](inst, *args)
            return inst
        if callable(fn): return fn(*args)

    # ---- Built-in functions ----

    # Output
    if name == 'say':
        print(' '.join(xcm_str(a) for a in args) if args else '')
        return None
    if name == 'say_inline':
        print(xcm_str(args[0]) if args else '', end='', flush=True)
        return None
    if name == 'say_error':
        print(xcm_str(args[0]) if args else '', file=sys.stderr)
        return None
    if name in ('say_red','say_green','say_yellow','say_blue','say_bold','say_cyan','say_magenta'):
        codes = {'say_red':31,'say_green':32,'say_yellow':33,'say_blue':34,
                 'say_bold':1,'say_cyan':36,'say_magenta':35}
        print(f"\x1b[{codes[name]}m{xcm_str(args[0]) if args else ''}\x1b[0m")
        return None
    if name in ('say_bg_red','say_bg_green','say_bg_yellow','say_bg_blue'):
        codes = {'say_bg_red':41,'say_bg_green':42,'say_bg_yellow':43,'say_bg_blue':44}
        print(f"\x1b[{codes[name]}m{xcm_str(args[0]) if args else ''}\x1b[0m")
        return None

    # Input
    if name == 'ask':
        try: return input(xcm_str(args[0]) if args else '')
        except EOFError: return ''
    if name == 'ask_int':
        prompt = xcm_str(args[0]) if args else ''
        while True:
            try: return int(float(input(prompt)))
            except ValueError: print("  Please enter a valid integer.")
    if name == 'ask_float':
        prompt = xcm_str(args[0]) if args else ''
        while True:
            try: return float(input(prompt))
            except ValueError: print("  Please enter a valid number.")
    if name == 'ask_secret':
        try: return _ask_secret_impl(xcm_str(args[0]) if args else 'Password: ')
        except KeyboardInterrupt: raise
        except: return ''

    # Type casting
    if name == 'int':
        try: return int(float(args[0])) if args else 0
        except: return 0
    if name == 'float':
        try: return float(args[0]) if args else 0.0
        except: return 0.0
    if name == 'string': return xcm_str(args[0]) if args else ''
    if name == 'bool':   return xcm_bool(args[0]) if args else False

    # Safe parsing
    if name == 'try_int':
        try: return int(float(args[0])) if args else None
        except: return None
    if name == 'try_float':
        try: return float(args[0]) if args else None
        except: return None

    # Type checks
    if name == 'type_of':
        val = args[0] if args else None
        if val is None:                  return 'maybe'
        if isinstance(val, bool):        return 'bool'
        if isinstance(val, (int,float)): return 'number'
        if isinstance(val, str):         return 'string'
        if isinstance(val, list):        return 'list'
        if isinstance(val, XCMInstance): return val._class.name
        if isinstance(val, dict):        return 'object'
        return 'unknown'
    if name == 'is_number':  return isinstance(args[0], (int,float)) and not isinstance(args[0], bool) if args else False
    if name == 'is_string':  return isinstance(args[0], str) if args else False
    if name == 'is_list':    return isinstance(args[0], list) if args else False
    if name == 'is_object':  return isinstance(args[0], (dict, XCMInstance)) if args else False
    if name == 'is_maybe':   return args[0] is None if args else True

    # Math
    if name == 'round':  return round(float(args[0]), int(args[1]) if len(args)>1 else 0) if args else 0
    if name == 'floor':  return int(math.floor(float(args[0]))) if args else 0
    if name == 'ceil':   return int(math.ceil(float(args[0]))) if args else 0
    if name == 'abs':    return abs(args[0]) if args else 0
    if name == 'sqrt':   return math.sqrt(float(args[0])) if args else 0
    if name == 'pow':    return math.pow(float(args[0]), float(args[1])) if len(args)>=2 else 0
    if name == 'log':    return math.log(float(args[0]), float(args[1]) if len(args)>1 else math.e) if args else 0
    if name == 'random':
        if len(args) == 0: return random.random()
        if len(args) == 1: return random.randint(0, int(args[0]))
        return random.randint(int(args[0]), int(args[1]))
    if name == 'random_float': return random.uniform(float(args[0]), float(args[1])) if len(args)>=2 else random.random()
    if name == 'max':    return max(args[0]) if len(args)==1 and isinstance(args[0],list) else (max(args) if args else None)
    if name == 'min':    return min(args[0]) if len(args)==1 and isinstance(args[0],list) else (min(args) if args else None)
    if name == 'sum':    return sum(args[0]) if args and isinstance(args[0],list) else sum(args)

    # String utilities
    if name == 'matches': return bool(re.search(str(args[1]), str(args[0]))) if len(args)>=2 else False
    if name == 'format':  return format(args[0], args[1]) if len(args)>=2 else xcm_str(args[0] if args else '')
    if name == 'len':     return len(args[0]) if args else 0
    if name == 'str':     return xcm_str(args[0]) if args else ''

    # Progress bar
    if name == 'progress_bar':
        current = int(args[0]) if args else 0
        total   = int(args[1]) if len(args)>1 else 100
        width   = int(args[2]) if len(args)>2 else 30
        pct     = current / total if total > 0 else 0
        filled  = int(width * pct)
        bar     = '=' * filled + ('>' if filled < width else '') + ' ' * (width - filled - (1 if filled < width else 0))
        print(f"\r  [{bar}] {int(pct*100)}%", end='', flush=True)
        if current >= total: print()
        return None

    # Print table
    if name == 'print_table':
        headers = args[0] if args else []
        rows    = args[1] if len(args)>1 else []
        widths  = [max(len(xcm_str(h)), max((len(xcm_str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
        sep     = '+' + '+'.join('-'*(w+2) for w in widths) + '+'
        def fmt_row(row):
            return '|' + '|'.join(f" {xcm_str(row[i]).ljust(widths[i])} " for i in range(len(headers))) + '|'
        print(sep)
        print(fmt_row(headers))
        print(sep)
        for row in rows: print(fmt_row(row))
        print(sep)
        return None

    # Timer & Date
    if name == 'start_timer': return time.time()
    if name == 'stop_timer':  return round(time.time() - float(args[0]), 3) if args else 0
    if name == 'date_now':
        import datetime
        now = datetime.datetime.now()
        return XCMObject(day=now.day, month=now.month, year=now.year,
                         hour=now.hour, minute=now.minute, second=now.second)

    # Wait
    if name == 'wait': time.sleep(float(args[0]) if args else 0); return None

    # JSON
    if name == 'json_parse':
        try: return json.loads(str(args[0])) if args else None
        except Exception as e: raise XCMError(f"json_parse failed: {e}", line_num)
    if name == 'json_stringify':
        indent = 2 if (len(args)>1 and args[1]) else None
        return json.dumps(args[0], indent=indent) if args else 'null'

    # Assert
    if name == 'assert':
        if args and not xcm_bool(args[0]):
            msg = xcm_str(args[1]) if len(args)>1 else 'Assertion failed'
            raise XCMError(msg, line_num)
        return None

    # System
    if name == 'clear': os.system('cls' if os.name == 'nt' else 'clear'); return None
    if name == 'exit':  sys.exit(int(args[0]) if args else 0)
    if name == 'beep':  print('\a', end='', flush=True); return None
    if name == 'argv':
        idx   = int(args[0]) if args else 0
        extra = sys.argv[3:]
        return extra[idx] if idx < len(extra) else None
    if name == 'env':   return os.environ.get(str(args[0])) if args else None

    # File I/O
    if name == 'read_file':
        p = str(args[0]) if args else ''
        if os.path.exists(p):
            with open(p,'r') as f: return f.read()
        raise XCMError(f"File not found: {p}", line_num)
    if name == 'write_file':
        if len(args)>=2:
            with open(str(args[0]),'w') as f: f.write(xcm_str(args[1]))
        return None
    if name == 'append_file':
        if len(args)>=2:
            with open(str(args[0]),'a') as f: f.write(xcm_str(args[1]))
        return None
    if name == 'file_exists': return os.path.exists(str(args[0])) if args else False
    if name == 'delete_file':
        if args and os.path.exists(str(args[0])): os.remove(str(args[0]))
        return None

    # Collections
    if name == 'list':  return []
    if name == 'range':
        if len(args)==1: return list(range(int(args[0])))
        if len(args)==2: return list(range(int(args[0]), int(args[1])))
        return []

    raise XCMError(f"Undefined function '{name}'", line_num)

# ============================================================
#  INTERPRETER
# ============================================================

class Interpreter:
    def __init__(self):
        self.global_env   = Environment()
        self.xcm_globals  = {}
        self.imported     = set()
        self.use_wingui   = False
        self.use_debug    = False
        self.current_file = ''
        self.global_env.set('__xcmGlobals', self.xcm_globals)

    def run_file(self, file_path):
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            print(f'XCM Error: File "{file_path}" not found.')
            return
        self.current_file = abs_path
        with open(abs_path,'r') as f: code = f.read()
        lines = code.splitlines()
        self.use_wingui = any(l.strip()=='use wingui' for l in lines)
        self.use_debug  = any(l.strip()=='use debug'  for l in lines)
        if self.use_wingui: print('[XCM] wingui active.')
        if self.use_debug:  print('[XCM] debug active.')
        self.imported.add(abs_path)
        self.execute_block(lines, self.global_env)

    def execute_block(self, lines, env):
        # Join multi-line expressions (lines ending with , or open brackets)
        joined = []
        buf = None
        for line in lines:
            raw = line.rstrip()
            s   = raw.lstrip()
            if buf is not None:
                buf += ' ' + s
                # check if balanced
                if self._is_balanced(buf.lstrip()):
                    joined.append(buf)
                    buf = None
            else:
                # detect unbalanced opening
                if s and not s.startswith('#') and not self._is_balanced(s):
                    buf = raw
                else:
                    joined.append(raw)
        if buf is not None:
            joined.append(buf)

        i = 0
        while i < len(joined):
            line     = joined[i]
            raw      = line.rstrip()
            stripped = raw.lstrip()
            indent   = len(raw) - len(stripped)
            if not stripped or stripped.startswith('#'): i+=1; continue
            if stripped in ('use wingui','use debug'):   i+=1; continue
            line_num = i + 1
            try:
                result = self.execute_line(stripped, indent, joined, i, env, line_num)
                i = result[1] if isinstance(result, tuple) and result[0]=='block' else i+1
            except (ReturnException, BreakException, ContinueException): raise
            except XCMError: raise
            except SystemExit: raise
            except Exception as e: raise XCMError(str(e), line_num, stripped)

    def _is_balanced(self, s):
        """Check if brackets/parens are balanced."""
        depth = 0; in_str = None
        for ch in s:
            if in_str:
                if ch == in_str: in_str = None
            elif ch in ('"', "'"): in_str = ch
            elif ch in ('(','[','{'): depth += 1
            elif ch in (')',']','}'): depth -= 1
        return depth == 0

    def execute_line(self, stripped, indent, all_lines, line_idx, env, line_num=None):

        # IMPORT
        m = re.match(r'^import\s+"([^"]+)"$', stripped)
        if m:
            imp_path = os.path.join(os.path.dirname(self.current_file), m.group(1))
            abs_imp  = os.path.abspath(imp_path)
            if abs_imp not in self.imported:
                self.imported.add(abs_imp)
                if os.path.exists(abs_imp):
                    with open(abs_imp,'r') as f: imp_lines = f.read().splitlines()
                    old = self.current_file; self.current_file = abs_imp
                    self.execute_block(imp_lines, env)
                    self.current_file = old
                else: raise XCMError(f'import "{m.group(1)}" not found', line_num)
            return None

        # ENUM
        m = re.match(r'^enum\s+(\w+)\s*:\s*(.+)$', stripped)
        if m:
            values = [v.strip() for v in m.group(2).split(',')]
            env.set(m.group(1), XCMEnum(m.group(1), values))
            return None

        # CLASS
        m = re.match(r'^class\s+(\w+)(?:\s+extends\s+(\w+))?\s*:$', stripped)
        if m:
            class_name = m.group(1)
            parent     = env.get(m.group(2)) if m.group(2) and env.has(m.group(2)) else None
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            methods = self._parse_class_body(body, env)
            cls = XCMClass(class_name, methods, parent)
            cls.closure_env = env
            env.set(class_name, cls)
            return ('block', next_i)

        # FUNCTION DEF
        m = re.match(r'^def\s+(\w+)\s*\((.*)\)\s*:$', stripped)
        if m:
            params = self._parse_params(m.group(2))
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            env.set(m.group(1), XCMFunction(m.group(1), params, body, env))
            return ('block', next_i)

        # LAMBDA ASSIGNMENT: var double = x => x * 2
        m = re.match(r'^(?:var|let|const)\s+(\w+)\s*=\s*(.+=>.*)', stripped)
        if m and '=>' in m.group(2):
            lm = re.match(r'^\(?([\w,\s]+)\)?\s*=>\s*(.+)$', m.group(2).strip())
            if lm:
                params = [p.strip() for p in lm.group(1).split(',')]
                body   = lm.group(2).strip()
                env.set(m.group(1), XCMLambda(params, body, env))
                return None

        # GLOBAL
        m = re.match(r'^global\s+(\w+)\s*=\s*(.+)$', stripped)
        if m:
            self.xcm_globals[m.group(1)] = eval_expr(m.group(2), env, line_num)
            return None
        if re.match(r'^global\s+\w+$', stripped): return None

        # IF CHAIN
        if re.match(r'^(if|elif)\s+.+:$', stripped) or stripped == 'else:':
            return self._exec_if_chain(all_lines, line_idx, indent, env, line_num)

        # MATCH
        m = re.match(r'^match\s+(.+):$', stripped)
        if m: return self._exec_match(m.group(1), all_lines, line_idx, indent, env, line_num)

        # LOOP
        m = re.match(r'^loop\((.+)\)\s*:$', stripped)
        if m:
            count = int(eval_expr(m.group(1), env, line_num) or 0)
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            for idx in range(count):
                lenv = Environment(env); lenv.set('i', idx)
                try: self.execute_block(body, lenv)
                except BreakException: break
                except ContinueException: continue
            return ('block', next_i)

        # REPEAT (loop without i variable)
        m = re.match(r'^repeat\((.+)\)\s*:$', stripped)
        if m:
            count = int(eval_expr(m.group(1), env, line_num) or 0)
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            for _ in range(count):
                try: self.execute_block(body, Environment(env))
                except BreakException: break
                except ContinueException: continue
            return ('block', next_i)

        # FOR IN RANGE
        m = re.match(r'^for\s+(\w+)\s+in\s+range\((\d+)(?:,\s*(\d+))?\)\s*:$', stripped)
        if m:
            v    = m.group(1)
            frm  = int(m.group(2)) if m.group(3) else 0
            to   = int(m.group(3)) if m.group(3) else int(m.group(2))
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            for idx in range(frm, to):
                lenv = Environment(env); lenv.set(v, idx)
                try: self.execute_block(body, lenv)
                except BreakException: break
                except ContinueException: continue
            return ('block', next_i)

        # FOR IN LIST
        m = re.match(r'^for\s+(\w+)\s+in\s+(.+):$', stripped)
        if m:
            iterable = eval_expr(m.group(2), env, line_num) or []
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            for item in iterable:
                lenv = Environment(env); lenv.set(m.group(1), item)
                try: self.execute_block(body, lenv)
                except BreakException: break
                except ContinueException: continue
            return ('block', next_i)

        # WHILE
        m = re.match(r'^while\s*\((.+)\)\s*:$', stripped)
        if m:
            cond_expr = m.group(1)
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            while xcm_bool(eval_expr(cond_expr, env, line_num)):
                try: self.execute_block(body, Environment(env))
                except BreakException: break
                except ContinueException: continue
            return ('block', next_i)

        # DO-WHILE
        if stripped == 'do:':
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            cond_expr = 'True'
            if next_i < len(all_lines):
                wl = all_lines[next_i].strip()
                wm = re.match(r'^while\s*\((.+)\)\s*:?$', wl)
                if wm: cond_expr = wm.group(1); next_i += 1
            while True:
                try: self.execute_block(body, Environment(env))
                except BreakException: break
                except ContinueException: pass
                if not xcm_bool(eval_expr(cond_expr, env, line_num)): break
            return ('block', next_i)

        # CHANCE
        m = re.match(r'^chance\((.+)\)\s*:$', stripped)
        if m:
            val = m.group(1)
            if '/' in val:
                n, d = val.split('/')
                prob = float(n.strip()) / float(d.strip())
            elif '%' in val:
                prob = float(val.replace('%','').strip()) / 100
            else:
                prob = float(eval_expr(val, env, line_num) or 0)
            body, next_i = self._collect_child(all_lines, line_idx, indent)
            if random.random() < prob:
                self.execute_block(body, Environment(env))
            return ('block', next_i)

        # TRY / CATCH
        if stripped == 'try:': return self._exec_try(all_lines, line_idx, indent, env, line_num)

        # RETURN
        m = re.match(r'^return(?:\s+(.+))?$', stripped)
        if m: raise ReturnException(eval_expr(m.group(1), env, line_num) if m.group(1) else None)

        # BREAK / CONTINUE
        if stripped == 'break':    raise BreakException()
        if stripped == 'continue': raise ContinueException()

        # THROW
        m = re.match(r'^throw\s+(.+)$', stripped)
        if m: raise XCMError(xcm_str(eval_expr(m.group(1), env, line_num)), line_num, stripped)

        # ASSERT
        m = re.match(r'^assert\s+(.+),\s*"([^"]+)"$', stripped)
        if m:
            if not xcm_bool(eval_expr(m.group(1), env, line_num)):
                raise XCMError(f'Assertion failed: {m.group(2)}', line_num, stripped)
            return None
        m = re.match(r'^assert\s+(.+)$', stripped)
        if m:
            if not xcm_bool(eval_expr(m.group(1), env, line_num)):
                raise XCMError('Assertion failed', line_num, stripped)
            return None

        # DELETE
        m = re.match(r'^delete\s+(\w+)$', stripped)
        if m: env.set(m.group(1), None); return None

        # WAIT
        m = re.match(r'^wait\((\d+(?:\.\d+)?)s\)$', stripped)
        if m: time.sleep(float(m.group(1))); return None

        # INCREMENT / DECREMENT
        if stripped.endswith('++'):
            vname = stripped[:-2].strip()
            cur   = env.get(vname) if env.has(vname) else 0
            env.assign(vname, (cur or 0) + 1); return None
        if stripped.endswith('--'):
            vname = stripped[:-2].strip()
            cur   = env.get(vname) if env.has(vname) else 0
            env.assign(vname, (cur or 0) - 1); return None

        # GUI
        gui_m = re.match(r'^(window|draw_box|draw_sprite|load_sprite|play_sound)\s*\((.+)\)$', stripped)
        if gui_m:
            if self.use_wingui:
                cmd = gui_m.group(1); params = gui_m.group(2)
                labels = {'window': f'[WINGUI] Window: {params}', 'draw_box': f'[WINGUI] RECT: {params}',
                          'draw_sprite': f'[WINGUI] SPRITE: {params}', 'load_sprite': f'[WINGUI] LOAD: {params}',
                          'play_sound': f'[WINGUI] AUDIO: {params}'}
                print(labels[cmd])
            return None

        # CONST
        m = re.match(r'^const\s+(\w+)\s*=\s*(.+)$', stripped)
        if m: env.set(m.group(1), eval_expr(m.group(2), env, line_num)); return None

        # MULTIPLE ASSIGNMENT: var x, y = 1, 2
        m = re.match(r'^(?:var|let)\s+([\w,\s]+)\s*=\s*(.+)$', stripped)
        if m:
            var_names = [v.strip() for v in m.group(1).split(',')]
            val_exprs = [v.strip() for v in split_outside(m.group(2), ',')]
            if len(var_names) > 1:
                for j, vname in enumerate(var_names):
                    env.set(vname, eval_expr(val_exprs[j] if j < len(val_exprs) else 'maybe', env, line_num))
            else:
                env.set(var_names[0], eval_expr(m.group(2), env, line_num))
            return None

        # COMPOUND ASSIGNMENT
        m = re.match(r'^(\w+)\s*(\+=|-=|\*=|/=|%=|\*\*=|//=)\s*(.+)$', stripped)
        if m:
            vname = m.group(1); op = m.group(2)
            rval  = eval_expr(m.group(3), env, line_num)
            cur   = env.get(vname) if env.has(vname) else 0
            ops   = {'+=':lambda a,b:a+b,'-=':lambda a,b:a-b,'*=':lambda a,b:a*b,
                     '/=':lambda a,b:a/b,'%=':lambda a,b:a%b,'**=':lambda a,b:a**b,
                     '//=':lambda a,b:int(a//b)}
            env.assign(vname, ops[op](cur or 0, rval)); return None

        # OBJ.ATTR = val
        m = re.match(r'^(\w+)\.(\w+)\s*=\s*(.+)$', stripped)
        if m:
            obj = env.get(m.group(1)) if env.has(m.group(1)) else None
            val = eval_expr(m.group(3), env, line_num)
            if isinstance(obj, (dict, XCMObject)): obj[m.group(2)] = val
            elif isinstance(obj, XCMInstance):     setattr(obj, m.group(2), val)
            return None

        # LIST[idx] = val
        m = re.match(r'^(\w+)\[(.+)\]\s*=\s*(.+)$', stripped)
        if m:
            obj = env.get(m.group(1)) if env.has(m.group(1)) else None
            idx = eval_expr(m.group(2), env, line_num)
            val = eval_expr(m.group(3), env, line_num)
            if isinstance(obj, list): obj[int(idx)] = val
            elif isinstance(obj, dict): obj[idx] = val
            return None

        # PLAIN ASSIGNMENT
        m = re.match(r'^(\w+)\s*=\s*(.+)$', stripped)
        if m and not re.match(r'^(if|elif|while|for|def|class|return|var|let|const|match|case|enum|import)\b', stripped):
            env.assign(m.group(1), eval_expr(m.group(2), env, line_num)); return None

        # EXPRESSION STATEMENT
        eval_expr(stripped, env, line_num)
        return None

    # --------------------------------------------------------
    #  HELPERS
    # --------------------------------------------------------

    def _collect_child(self, lines, start_idx, parent_indent):
        body = []; next_i = start_idx + 1
        while next_i < len(lines):
            cl = lines[next_i].rstrip(); cs = cl.lstrip(); ci = len(cl)-len(cs)
            if cs and ci <= parent_indent: break
            body.append(lines[next_i]); next_i += 1
        return body, next_i

    def _parse_params(self, params_str):
        params_str = params_str.strip()
        if not params_str: return []
        result = []
        for part in split_args(params_str):
            part = part.strip()
            if '=' in part:
                name, default = part.split('=', 1)
                result.append((name.strip(), eval_expr(default.strip(), self.global_env)))
            else:
                result.append((part, None))
        return result

    def _parse_class_body(self, body_lines, env):
        methods = {}; i = 0
        while i < len(body_lines):
            line = body_lines[i].rstrip(); stripped = line.lstrip(); indent = len(line)-len(stripped)
            m = re.match(r'^def\s+(\w+)\s*\((.*)\)\s*:$', stripped)
            if m:
                fn_name    = m.group(1)
                param_list = [p.strip() for p in split_args(m.group(2)) if p.strip()]
                if param_list and param_list[0] == 'self': param_list = param_list[1:]
                params = []
                for p in param_list:
                    if '=' in p:
                        n, d = p.split('=',1); params.append((n.strip(), eval_expr(d.strip(), env)))
                    else: params.append((p, None))
                fn_body, next_i = self._collect_child(body_lines, i, indent)
                def make_method(fn_name, params, fn_body, env, interp_ref):
                    def method(self_inst, *args):
                        local_env = Environment(env)
                        local_env.set('self', self_inst)
                        for j, (pname, pdefault) in enumerate(params):
                            local_env.set(pname, args[j] if j < len(args) else pdefault)
                        sub = Interpreter()
                        sub.global_env   = env
                        sub.xcm_globals  = interp_ref.xcm_globals
                        sub.use_wingui   = interp_ref.use_wingui
                        sub.current_file = interp_ref.current_file
                        try:    sub.execute_block(fn_body, local_env)
                        except ReturnException as r: return r.value
                        return None
                    method.name = fn_name; return method
                methods[fn_name] = make_method(fn_name, params, fn_body, env, self)
                i = next_i
            else: i += 1
        return methods

    def _exec_if_chain(self, lines, start_idx, indent, env, line_num=None):
        i = start_idx; executed = False
        while i < len(lines):
            line = lines[i].rstrip(); stripped = line.lstrip(); ci = len(line)-len(stripped)
            if stripped and ci < indent: break
            if stripped and ci > indent: i+=1; continue
            m_if   = re.match(r'^(if|elif)\s+(.+)\s*:$', stripped)
            m_else = (stripped == 'else:')
            if m_if:
                if m_if.group(1)=='if' and i!=start_idx: break
                cond  = xcm_bool(eval_expr(m_if.group(2), env, line_num)) if not executed else False
                body, next_i = self._collect_child(lines, i, ci)
                if cond and not executed:
                    self.execute_block(body, Environment(env)); executed = True
                i = next_i
            elif m_else:
                body, next_i = self._collect_child(lines, i, ci)
                if not executed: self.execute_block(body, Environment(env))
                i = next_i; break
            else: break
        return ('block', i)

    def _exec_match(self, var_expr, lines, start_idx, indent, env, line_num=None):
        val = eval_expr(var_expr, env, line_num)
        body, next_i = self._collect_child(lines, start_idx, indent)
        matched = False; i = 0
        while i < len(body):
            bl = body[i].rstrip(); bs = bl.lstrip(); bi = len(bl)-len(bs)
            m_case    = re.match(r'^case\s+(.+):$', bs)
            m_default = (bs == 'default:')
            if m_case:
                case_val  = eval_expr(m_case.group(1), env, line_num)
                case_body, next_j = self._collect_child(body, i, bi)
                if not matched and val == case_val:
                    self.execute_block(case_body, Environment(env)); matched = True
                i = next_j
            elif m_default:
                def_body, next_j = self._collect_child(body, i, bi)
                if not matched: self.execute_block(def_body, Environment(env))
                i = next_j
            else: i += 1
        return ('block', next_i)

    def _exec_try(self, lines, start_idx, indent, env, line_num=None):
        try_body, next_i = self._collect_child(lines, start_idx, indent)
        catch_body = []; err_var = 'e'
        if next_i < len(lines):
            cl = lines[next_i].rstrip(); cs = cl.lstrip(); ci = len(cl)-len(cs)
            m  = re.match(r'^catch(?:\((\w+)\))?\s*:$', cs)
            if m and ci == indent:
                err_var = m.group(1) or 'e'
                catch_body, next_i = self._collect_child(lines, next_i, indent)
        try:
            self.execute_block(try_body, Environment(env))
        except (XCMError, Exception) as e:
            err_obj   = XCMObject(message=str(e))
            catch_env = Environment(env)
            catch_env.set(err_var, err_obj)
            self.execute_block(catch_body, catch_env)
        return ('block', next_i)

# ============================================================
#  ENTRY POINT
# ============================================================

def main():
    args = sys.argv[1:]
    if not args:
        print(f"""
╔══════════════════════════════════════════╗
║         XCM Language Engine             ║
║         Version 1.0.0                    ║
╠══════════════════════════════════════════╣
║  xcm run <file.xcm>   Run a XCM file    ║
║  xcm version          Show version      ║
╠══════════════════════════════════════════╣
║  Flags (top of .xcm file):              ║
║    use wingui   Enable graphics         ║
║    use debug    Show debug info         ║
╚══════════════════════════════════════════╝""")
    elif args[0] == 'run' and len(args) >= 2:
        try:
            Interpreter().run_file(args[1])
        except XCMError as e:  print(f'\n{e}', file=sys.stderr)
        except KeyboardInterrupt: print('\nInterrupted.')
        except SystemExit: pass
    elif args[0] in ('version', '-v'):
        print(f'XCM Engine v{XCM_VERSION}')
    else:
        print(f'XCM Error: Unknown command "{args[0]}"')
        print('Usage: xcm run <file.xcm>')

if __name__ == '__main__':
    main()
