from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import TBinOp, TBool, TIf, TInt, TLam, TString, TUnOp, TVar, Term
from printer import encode_string, to_base94


MAX_STEPS = 10_000_000


class InterpreterError(Exception):
    pass


class BetaReductionLimit(InterpreterError):
    pass


class ScopeError(InterpreterError):
    pass


class TypeError_(InterpreterError):
    pass


class ArithmeticError_(InterpreterError):
    pass


class UnknownUnOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown unary operator: {op}")
        self.op = op


class UnknownBinOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown binary operator: {op}")
        self.op = op


@dataclass
class VInt:
    value: int


@dataclass
class VBool:
    value: bool


@dataclass
class VString:
    value: str


@dataclass
class VClosure:
    var: int
    body: Term
    env: dict[int, "Thunk"]


Value = VInt | VBool | VString | VClosure


@dataclass
class Thunk:
    kind: str
    value: Value | None = None
    steps: int = 0
    term: Term | None = None
    env: dict[int, "Thunk"] | None = None


def _to_term(v: Value) -> Term:
    if isinstance(v, VInt):
        return TInt(v.value)
    if isinstance(v, VBool):
        return TBool(v.value)
    if isinstance(v, VString):
        return TString(v.value)
    if isinstance(v, VClosure):
        return TLam(v.var, v.body)
    raise TypeError(f"Unknown value type: {type(v).__name__}")


def interpret(check_max: bool, term: Term) -> tuple[Term, int]:
    steps = 0
    
    def eval_term(t: Term, env: dict[int, Thunk]) -> Value:
        # TODO
        nonlocal steps
        #Literals
        if isinstance(t, TInt):
            return VInt(t.value)
        if isinstance(t, TString):
            return VString(t.value)
        if isinstance(t, TBool):
            return VBool(t.value)
        #Lambdas
        if isinstance(t, TLam):
            return VClosure(t.var, t.body, env.copy())
        #Variables
        if isinstance(t, TVar):
            if t.value not in env:
                raise ScopeError(f"Unbound variable: {t.value}")
            thunk = env[t.value]
            return eval_term(thunk.term, thunk.env)
        #Condition
        if isinstance(t, TIf):
            cond_val = eval_term(t.cond, env)
            if not isinstance(cond_val, VBool):
                raise TypeError_("Condition must be a boolean")
                
            if cond_val.value is True:
                return eval_term(t.true_branch, env)
            else:
                return eval_term(t.false_branch, env)
        #Function Application
        if isinstance(t, TBinOp) and t.op == "$":
            func_val = eval_term(t.left, env)
            if not isinstance(func_val, VClosure):
                raise TypeError_("Left side of application must be a function")
            steps += 1
            if check_max and steps > MAX_STEPS:
                raise BetaReductionLimit()
            arg_thunk = Thunk(kind="lazy", term=t.right, env=env)
            new_env = func_val.env.copy()
            new_env[func_val.var] = arg_thunk
            return eval_term(func_val.body, new_env)
        #Unary Operations
        if isinstance(t, TUnOp):
            child_val = eval_term(t.term, env)
            if t.op == "-":
                if not isinstance(child_val, VInt): raise TypeError_()
                return VInt(-child_val.value)
            elif t.op == "!":
                if not isinstance(child_val, VBool): raise TypeError_()
                return VBool(not child_val.value)
            elif t.op == "#":
                if not isinstance(child_val, VString): raise TypeError_()
                result = 0
                for ch in child_val.value:
                    result = result * 94 + (ord(ch) - 33)
                return VInt(result)
            elif t.op == "$":
                if not isinstance(child_val, VInt): raise TypeError_()
                return VString(to_base94(child_val.value))
            else:
                raise UnknownUnOp(t.op)
        #Binary Operations
        if isinstance(t, TBinOp):
            left_val = eval_term(t.left, env)
            right_val = eval_term(t.right, env)
            if t.op == "+":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                return VInt(left_val.value + right_val.value)
            elif t.op == "/":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                if right_val.value == 0: raise ArithmeticError_()
                return VInt(int(left_val.value / right_val.value))
            elif t.op == "-":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                return VInt(left_val.value - right_val.value)
            elif t.op == "*":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                return VInt(left_val.value * right_val.value)
            elif t.op == "%":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                if right_val.value == 0: raise ArithmeticError_()
                return VInt(left_val.value % right_val.value)
            elif t.op == "<":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                return VBool(left_val.value < right_val.value)
            elif t.op == ">":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                return VBool(left_val.value > right_val.value)
            elif t.op == "=":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VInt): raise TypeError_()
                return VBool(left_val.value == right_val.value)
            elif t.op == "|":
                if not isinstance(left_val, VBool) or not isinstance(right_val, VBool): raise TypeError_()
                return VBool(left_val.value or right_val.value)
            elif t.op == "&":
                if not isinstance(left_val, VBool) or not isinstance(right_val, VBool): raise TypeError_()
                return VBool(left_val.value and right_val.value)
            elif t.op == ".":
                if not isinstance(left_val, VString) or not isinstance(right_val, VString): raise TypeError_()
                return VString(left_val.value + right_val.value)
            elif t.op == "T":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VString): raise TypeError_()
                return VString(right_val.value[:left_val.value])
            elif t.op == "D":
                if not isinstance(left_val, VInt) or not isinstance(right_val, VString): raise TypeError_()
                return VString(right_val.value[left_val.value:])
            else:
                raise UnknownBinOp(t.op)
                
        raise TypeError(f"Unknown term type: {type(t).__name__}")
    

    result = eval_term(term, {})
    return _to_term(result), steps
