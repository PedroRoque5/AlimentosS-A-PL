from flask import Flask, request, send_file, jsonify
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, value, LpStatus
import re

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/resolver', methods=['POST'])
def resolver():
    try:
        variaveis_raw = request.form['variaveis']
        objetivo_raw = request.form['objetivo']
        restricoes_raw = request.form.getlist('ref[]')
        operadores = request.form.getlist('op[]')
        valores = request.form.getlist('valor[]')

        variaveis = [v.strip() for v in variaveis_raw.split(',') if v.strip()]
        if not variaveis:
            raise ValueError("Você deve informar pelo menos uma variável.")
        var_dict = {v: LpVariable(v, lowBound=0) for v in variaveis}

        problema = LpProblem("Dieta_Saudavel", LpMinimize)
        problema += parse_expressao(objetivo_raw, var_dict), "Custo_Total"

        expressoes_nutricionais = {
            "Vitamina A": "2*leite + 2*carne + 10*peixe + 20*salada",
            "Vitamina C": "50*leite + 20*carne + 10*peixe + 30*salada",
            "Vitamina D": "80*leite + 70*carne + 10*peixe + 80*salada"
        }

        for ref, op, val in zip(restricoes_raw, operadores, valores):
            ref = ref.strip()
            if not ref:
                continue

            if ref in expressoes_nutricionais:
                expr_str = expressoes_nutricionais[ref]
            else:
                raise ValueError(f"Exigência desconhecida: '{ref}'")

            expr = parse_expressao(expr_str, var_dict)
            val = float(val)

            if op == ">=":
                problema += expr >= val
            elif op == "<=":
                problema += expr <= val
            elif op == "=":
                problema += expr == val
            else:
                raise ValueError(f"Operador inválido: '{op}'")

        # Resolve o problema e guarda o status
        status = problema.solve()

        # Se não for solução ótima ou factível, avisa
        if LpStatus[status] != 'Optimal':
            return jsonify({
                "status": LpStatus[status],
                "mensagem": "Problema não tem solução ótima."
            })

        # Monta o resultado
        resultado = {
            "status": LpStatus[status],
            "custo_total": round(value(problema.objective), 2),
            "quantidades": {}
        }

        for v in problema.variables():
            val = v.varValue
            # Arredonda ou define 0 para None
            resultado["quantidades"][v.name] = round(val, 2) if val is not None else 0

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


def parse_expressao(expr_str, var_dict):
    expr_str = expr_str.replace('-', '+-')
    termos = expr_str.split('+')
    expr = 0
    for termo in termos:
        termo = termo.strip()
        if not termo:
            continue
        match = re.match(r'([\-]?\d*\.?\d*)\s*\*\s*([a-zA-Z_][a-zA-Z0-9_]*)', termo)
        if not match:
            raise ValueError(f"Erro no termo: '{termo}' (use formato como 2*leite)")
        coef_str, var_name = match.groups()
        coef = float(coef_str) if coef_str not in ['', '-'] else float(coef_str + '1')
        if var_name not in var_dict:
            raise ValueError(f"Variável não reconhecida: '{var_name}'")
        expr += coef * var_dict[var_name]
    return expr


if __name__ == '__main__':
    app.run(debug=True)
