from werkzeug.security import generate_password_hash

senha = "34015030"

# gerar o hash compatível com o sistema de login
hash_senha = generate_password_hash(senha)

print(hash_senha)
