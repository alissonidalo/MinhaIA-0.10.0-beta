# libs/utils.py

import random
import string

def generate_string(length=8):
    """
    Gera uma string aleatória de tamanho especificado.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
