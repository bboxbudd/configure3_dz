#!/usr/bin/env python3
import sys
import re
import yaml

class ConfigLanguageError(Exception):
    """Исключение для синтаксических ошибок конфигурационного языка."""
    pass

class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def error(self, message):
        raise ConfigLanguageError(f"Ошибка на строке {self.line}, позиция {self.col}: {message}")

    def skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

    def match(self, pattern):
        self.skip_whitespace()
        match = re.match(pattern, self.text[self.pos:])
        if not match:
            self.error(f"Ожидается токен, соответствующий регулярному выражению: {pattern}")
        token = match.group(0)
        self.pos += len(token)
        self.col += len(token)
        return token

    def parse_number(self):
        num_str = self.match(r'\d+')
        return int(num_str)

    def parse_identifier(self):
        ident = self.match(r'[_a-z]+')
        return ident

    def parse_string(self):
        self.match(r'"')
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != '"':
            if self.text[self.pos] == '\\':
                self.pos += 1
                if self.pos >= len(self.text):
                    break
            self.pos += 1
        if self.pos >= len(self.text) or self.text[self.pos] != '"':
            self.error("Незакрытая строка")
        s = self.text[start:self.pos]
        self.match(r'"')
        return s

    def parse_dict(self):
        self.match(r'{')
        result = {}
        first = True
        while self.pos < len(self.text):
            self.skip_whitespace()
            if self.pos < len(self.text) and self.text[self.pos] == '}':
                break
            if not first:
                self.match(r',')
            key = self.parse_identifier()
            self.match(r'=>')
            value = self.parse_value()
            result[key] = value
            first = False
        self.match(r'}')
        return result

    def parse_value(self):  
        self.skip_whitespace()
        if self.pos >= len(self.text):
            self.error("Неожиданный конец входных данных")

        char = self.text[self.pos]
        if char.isdigit():
            return self.parse_number()
        elif char == '"':
            return self.parse_string()
        elif char == '{':
            return self.parse_dict()
        elif char == '$':
            return self.parse_var()
        else:
            self.error("Ожидается число, строка, словарь или переменная ($[имя])")

    def parse_let(self):
        self.match(r'let')
        name = self.parse_identifier()
        self.match(r'=')
        value = self.parse_value()
        return ('let', name, value)

    def parse_q(self):
        self.match(r'q\(')
        expr = self.parse_value()
        self.match(r'\)')
        return ('q', expr)

    def parse_var(self):
        self.match(r'\$')
        self.match(r'\[')
        name = self.parse_identifier()
        self.match(r'\]')
        return ('var', name)

    def parse_expression(self):
        self.skip_whitespace()
        if self.pos < len(self.text) and self.text[self.pos] == '$':
            return self.parse_var()
        else:
            return self.parse_value()

    def parse_statement(self):
        self.skip_whitespace()
        if self.pos >= len(self.text):
            return None
        if self.text.startswith('let', self.pos):
            return self.parse_let()
        elif self.text.startswith('q(', self.pos):
            return self.parse_q()
        else:
            return self.parse_expression()

    def parse_all(self):
        statements = []
        while self.pos < len(self.text):
            self.skip_whitespace()
            if self.pos >= len(self.text):
                break
            stmt = self.parse_statement()
            if stmt is None:
                break
            statements.append(stmt)
        return statements

class Interpreter:
    def __init__(self):
        self.variables = {}

    def evaluate(self, ast):
        if ast is None:
            return
        if isinstance(ast, tuple):
            if ast[0] == 'let':
                _, name, value = ast
                self.variables[name] = self._eval_value(value)
            elif ast[0] == 'q':
                _, expr = ast
                result = self._eval_value(expr)
                # Вывод в YAML
                print(yaml.dump(result, allow_unicode=True, default_flow_style=False).rstrip())
            elif ast[0] == 'var':
                _, name = ast
                if name not in self.variables:
                    raise ConfigLanguageError(f"Переменная '{name}' не определена")
                return self.variables[name]
            else:
                raise ConfigLanguageError(f"Неизвестный узел AST: {ast}")
        else:
            return ast

    def _eval_value(self, value):
        if isinstance(value, dict):
            return {k: self._eval_value(v) for k, v in value.items()}
        elif isinstance(value, tuple) and value[0] == 'var':
            return self.evaluate(value)
        else:
            return value

def main():
    if len(sys.argv) != 2:
        print("Использование: python config_parser.py <путь_к_файлу>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл '{filepath}' не найден.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        parser = Parser(content)
        ast = parser.parse_all()
    except ConfigLanguageError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    interpreter = Interpreter()
    try:
        for stmt in ast:
            interpreter.evaluate(stmt)
    except ConfigLanguageError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()