"""
=============================================================================
ESCOLA DO FUTURO — EE ANTONIO REGINATO
Backend de Autenticação e Gestão de Usuários com FastAPI
=============================================================================
Compatível com Python 3.10, 3.11, 3.12 e 3.13.
Utiliza bcrypt direto para hash de senhas (evitando bugs do passlib no Python 3.13),
lifespan moderno do FastAPI, persistência SQLite e entrega de index.html.
"""

import os
import re
import hmac
import base64
import hashlib
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES DE SEGURANÇA E AMBIENTE
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "escola_do_futuro_secret_key_reginato_2024_secure_jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escola_auth.db")
INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
PAINEL_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel.html")

# ---------------------------------------------------------------------------
# SISTEMA DE CRIPTOGRAFIA DE SENHAS (BCRYPT NATIVO + FALLBACK PBKDF2)
# ---------------------------------------------------------------------------
# Evita o passlib (descontinuado e incompatível com bcrypt >= 4 no Python 3.13).
# Usa bcrypt diretamente, com suporte seguro a truncamento em 72 bytes.
try:
    import bcrypt
    USE_BCRYPT = True
except ImportError:
    USE_BCRYPT = False


def hash_password(password: str) -> str:
    """Gera o hash seguro da senha com bcrypt ou PBKDF2 nativo."""
    if USE_BCRYPT:
        # O algoritmo bcrypt aceita até 72 bytes no segredo
        pwd_bytes = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    # Fallback seguro nativo PBKDF2 (padrão Python sem bibliotecas C externas)
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return "pbkdf2$" + base64.b64encode(salt).decode("utf-8") + "$" + base64.b64encode(key).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    if not hashed_password or not plain_password:
        return False

    # Se foi gerado com o fallback PBKDF2
    if hashed_password.startswith("pbkdf2$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            salt = base64.b64decode(parts[1])
            expected_key = base64.b64decode(parts[2])
            new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
            return hmac.compare_digest(new_key, expected_key)
        return False

    # Verificação com bcrypt direto
    if USE_BCRYPT:
        try:
            pwd_bytes = plain_password.encode("utf-8")[:72]
            return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
        except Exception:
            return False

    return False


# ---------------------------------------------------------------------------
# GERAÇÃO E DECODIFICAÇÃO DE TOKENS JWT
# ---------------------------------------------------------------------------
try:
    from jose import jwt
    USE_JOSE = True
except ImportError:
    try:
        import jwt
        USE_JOSE = True
    except ImportError:
        USE_JOSE = False


def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_url_decode(s: str) -> bytes:
    padding = '=' * (4 - (len(s) % 4))
    return base64.urlsafe_b64decode(s + padding)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Gera um JWT assinado com tempo de expiração."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp())})

    if USE_JOSE:
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Fallback nativo HS256 em puro Python (sempre disponível)
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    part1 = _b64_url_encode(header_json)
    part2 = _b64_url_encode(payload_json)
    signing_input = f"{part1}.{part2}".encode("utf-8")

    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    part3 = _b64_url_encode(signature)

    return f"{part1}.{part2}.{part3}"


def decode_access_token(token: str) -> Optional[dict]:
    """Decodifica e valida a assinatura e expiração do JWT."""
    if USE_JOSE:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except Exception:
            return None

    # Fallback nativo HS256
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _b64_url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _b64_url_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Validação de Expiração
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None

        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# BANCO DE DADOS SQLITE E TABELAS
# ---------------------------------------------------------------------------
DEFAULT_USERS = [
    {
        "name": "Administrador Reginato",
        "email": "admin@escola.sp.gov.br",
        "password": "admin123",
        "role": "gestor",
    },
    {
        "name": "Gestor Pedagógico Reginato",
        "email": "gestor@escola.sp.gov.br",
        "password": "gestor123",
        "role": "gestor",
    },
    {
        "name": "Prof. Carlos Eduardo",
        "email": "professor@escola.sp.gov.br",
        "password": "professor123",
        "role": "professor",
    },
    {
        "name": "Diretora Ana Paula",
        "email": "diretor@escola.sp.gov.br",
        "password": "diretor123",
        "role": "diretor",
    },
]

ALLOWED_ROLES = {"aluno", "professor", "gestor", "diretor"}

REPORTS_CATALOG = {
    "saresp": {
        "id": 1,
        "codigo": "#REL-01",
        "slug": "saresp",
        "titulo": "Desempenho SARESP e Avaliações Diagnósticas 2026",
        "classificacao": "Restrito à Gestão",
        "perfis_permitidos": ["gestor", "diretor"],
        "endpoint": "/api/relatorios/saresp",
        "descricao": "Consolidado de proficiência em Língua Portuguesa, Matemática e evolução IDESP por série.",
    },
    "diario-classe": {
        "id": 2,
        "codigo": "#REL-02",
        "slug": "diario-classe",
        "titulo": "Diário de Classe & Lançamento de Médias Bimestrais",
        "classificacao": "Professores / Gestão",
        "perfis_permitidos": ["professor", "gestor", "diretor"],
        "endpoint": "/api/relatorios/diario-classe",
        "descricao": "Acompanhamento de aulas ministradas, frequência por turma e fechamento de médias bimestrais.",
    },
    "auditoria-matriculas": {
        "id": 3,
        "codigo": "#REL-03",
        "slug": "auditoria-matriculas",
        "titulo": "Auditoria de Matrículas e Frequência Escolar",
        "classificacao": "Exclusivo Diretoria",
        "perfis_permitidos": ["diretor"],
        "endpoint": "/api/relatorios/auditoria-matriculas",
        "descricao": "Conferência de matrículas ativas, transferências, busca ativa escolar e conformidade SED.",
    },
}


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa as tabelas do banco de dados e garante os usuários padrão pedagógicos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'professor',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        now_iso = datetime.now(timezone.utc).isoformat()
        for default_user in DEFAULT_USERS:
            cursor.execute("SELECT id FROM users WHERE email = ?", (default_user["email"],))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (name, email, hashed_password, role, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    default_user["name"],
                    default_user["email"],
                    hash_password(default_user["password"]),
                    default_user["role"],
                    1,
                    now_iso,
                ))
        conn.commit()


def find_user_by_identifier(cursor, identifier: str):
    """Localiza usuário por e-mail completo ou usuário institucional (ex.: gestor, professor, diretor)."""
    identifier_clean = identifier.lower().strip()
    cursor.execute("SELECT * FROM users WHERE email = ?", (identifier_clean,))
    user = cursor.fetchone()
    if user or "@" in identifier_clean:
        return user
    institutional_email = f"{identifier_clean}@escola.sp.gov.br"
    cursor.execute("SELECT * FROM users WHERE email = ?", (institutional_email,))
    return cursor.fetchone()


def build_token_response(user: sqlite3.Row) -> dict:
    """Monta o payload JWT e a resposta padronizada de autenticação."""
    token_payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
    }
    token = create_access_token(token_payload)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "is_active": bool(user["is_active"]),
            "created_at": user["created_at"],
        },
    }


def authorize_report_access(report_slug: str, current_user: dict) -> dict:
    """Valida se o perfil do usuário autenticado tem permissão para consultar o relatório."""
    report = REPORTS_CATALOG[report_slug]
    user_role = (current_user.get("role") or "").lower().strip()
    if user_role not in report["perfis_permitidos"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "erro": "Acesso negado por controle de perfil (RBAC).",
                "codigo_relatorio": report["codigo"],
                "titulo_relatorio": report["titulo"],
                "classificacao_exigida": report["classificacao"],
                "perfis_permitidos": report["perfis_permitidos"],
                "seu_perfil": user_role,
                "mensagem": (
                    f"O perfil '{user_role}' não possui permissão para consultar "
                    f"o relatório {report['codigo']} ({report['classificacao']})."
                ),
            },
        )
    return report


# ---------------------------------------------------------------------------
# ESQUEMAS PYDANTIC (VALIDAÇÃO DE ENTRADA E SAÍDA)
# ---------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="E-mail institucional")
    password: str = Field(..., min_length=6, max_length=128, description="Senha de acesso")
    role: Optional[str] = Field("professor", description="Perfil: professor, gestor, diretor ou aluno")


class UserLoginRequest(BaseModel):
    email: Optional[str] = Field(None, description="E-mail ou nome de usuário")
    username: Optional[str] = Field(None, description="Compatibilidade com campo username")
    password: Optional[str] = Field(None, description="Senha")
    senha: Optional[str] = Field(None, description="Compatibilidade com formulário pedagógico")


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# CICLO DE VIDA (LIFESPAN HANDLER MODERNO DO FASTAPI)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executado na inicialização e encerramento da aplicação."""
    init_db()
    yield


# ---------------------------------------------------------------------------
# APLICAÇÃO FASTAPI & MIDDLEWARES
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Escola do Futuro — EE Antonio Reginato",
    description="API de Autenticação e Gestão de Credenciais com FastAPI e JWT",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Habilita CORS para requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


# ---------------------------------------------------------------------------
# DEPENDÊNCIA DE AUTENTICAÇÃO (PROTEÇÃO DE ENDPOINTS)
# ---------------------------------------------------------------------------
def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> dict:
    """Valida o Bearer Token e retorna os dados do usuário autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acesso inválido, ausente ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo ou inexistente.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return dict(user)


# ---------------------------------------------------------------------------
# ENDPOINTS DA APLICAÇÃO
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_index():
    """Entrega o arquivo index.html da interface web."""
    if os.path.exists(INDEX_HTML_PATH):
        return FileResponse(INDEX_HTML_PATH)
    return HTMLResponse("<h1>Escola do Futuro — Arquivo index.html não localizado</h1>", status_code=404)


@app.get("/painel", response_class=HTMLResponse, tags=["Frontend"])
def serve_painel():
    """Entrega o arquivo painel.html da área restrita pedagógica."""
    if os.path.exists(PAINEL_HTML_PATH):
        return FileResponse(PAINEL_HTML_PATH)
    return HTMLResponse("<h1>Escola do Futuro — Arquivo painel.html não localizado</h1>", status_code=404)


@app.get("/painel-servidor", response_class=HTMLResponse, tags=["Área Restrita"])
def serve_painel_com_bloqueio_servidor(token: Optional[str] = None):
    """
    Demonstração pedagógica de bloqueio a nível de servidor:
    Se acessado diretamente no navegador sem o parâmetro ?token=... ou token inválido,
    o FastAPI interrompe a renderização imediatamente com HTTP 401.
    """
    if not token or not decode_access_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ACESSO NEGADO PELO SERVIDOR: É obrigatório autenticar-se para receber esta página HTML."
        )
    return FileResponse(PAINEL_HTML_PATH)


@app.get("/api/dados-restritos", tags=["Área Restrita"])
def get_dados_restritos(current_user: dict = Depends(get_current_user)):
    """
    Endpoint protegido: Requer Token JWT válido no cabeçalho 'Authorization: Bearer <token>'.
    Se acessado diretamente sem token, o FastAPI retorna automaticamente HTTP 401 Unauthorized.
    Retorna os dados confidenciais pedagógicos (notas, turmas, relatórios) com permissões por perfil.
    """
    user_role = (current_user.get("role") or "").lower().strip()
    relatorios_lista = []
    for report in REPORTS_CATALOG.values():
        permitido = user_role in report["perfis_permitidos"]
        relatorios_lista.append({
            "id": report["id"],
            "codigo": report["codigo"],
            "slug": report["slug"],
            "titulo": report["titulo"],
            "classificacao": report["classificacao"],
            "perfis_permitidos": report["perfis_permitidos"],
            "endpoint": report["endpoint"],
            "permitido": permitido,
            "status": "Disponível" if permitido else "Bloqueado para este Perfil",
        })

    return {
        "status": "autorizado",
        "mensagem": "Acesso concedido com sucesso aos dados confidenciais da EE Antonio Reginato.",
        "usuario": {
            "id": current_user["id"],
            "nome": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
        },
        "dados_sigilosos": {
            "ano_letivo": 2026,
            "escola": "Escola Estadual Antonio Reginato",
            "turmas_ativas": 14,
            "media_geral_escola": 8.4,
            "relatorios": relatorios_lista,
        },
    }


@app.get("/api/relatorios/saresp", tags=["Relatórios Pedagógicos"])
def get_relatorio_saresp(current_user: dict = Depends(get_current_user)):
    """
    #REL-01: Desempenho SARESP e Avaliações Diagnósticas 2026.
    Classificação: Restrito à Gestão (perfis permitidos: gestor, diretor).
    """
    report = authorize_report_access("saresp", current_user)
    return {
        "status": "autorizado",
        "relatorio": report,
        "consultado_por": {
            "nome": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
        },
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "resumo": {
            "participacao_geral": "94,2%",
            "media_lingua_portuguesa": 8.2,
            "media_matematica": 8.6,
            "meta_idesp_2026": "Superada (+0,5)",
        },
        "colunas": ["Série / Ano", "Turmas", "Média LP", "Média Mat", "Nível Adequado", "Evolução vs 2025"],
        "registros": [
            {"serie": "6º Ano EF", "turmas": "3 salas", "media_lp": "8,1", "media_mat": "8,3", "nivel_adequado": "79%", "evolucao": "+4,2%"},
            {"serie": "9º Ano EF", "turmas": "4 salas", "media_lp": "8,3", "media_mat": "8,7", "nivel_adequado": "82%", "evolucao": "+5,8%"},
            {"serie": "1ª Série EM", "turmas": "4 salas", "media_lp": "8,0", "media_mat": "8,5", "nivel_adequado": "77%", "evolucao": "+3,9%"},
            {"serie": "3ª Série EM", "turmas": "3 salas", "media_lp": "8,5", "media_mat": "8,9", "nivel_adequado": "86%", "evolucao": "+6,1%"},
        ],
        "observacoes_pedagogicas": [
            "Meta SARESP 2026 superada em todas as séries avaliadas no Ensino Fundamental II e Médio.",
            "Recomenda-se plano de recomposição focalizada em geometria analítica para a 1ª Série EM.",
            "Dados sintéticos para demonstração pedagógica de autorização RBAC (Restrito à Gestão).",
        ],
    }


@app.get("/api/relatorios/diario-classe", tags=["Relatórios Pedagógicos"])
def get_relatorio_diario_classe(current_user: dict = Depends(get_current_user)):
    """
    #REL-02: Diário de Classe & Lançamento de Médias Bimestrais.
    Classificação: Professores / Gestão (perfis permitidos: professor, gestor, diretor).
    """
    report = authorize_report_access("diario-classe", current_user)
    return {
        "status": "autorizado",
        "relatorio": report,
        "consultado_por": {
            "nome": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
        },
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "resumo": {
            "bimestre_referencia": "4º Bimestre / 2026",
            "turmas_com_notas_lancadas": "14 / 14",
            "media_geral_bimestre": 8.4,
            "estudantes_em_recuperacao": 27,
        },
        "colunas": ["Turma", "Componente Curricular", "Docente Responsável", "Aulas Dadas", "Média Turma", "Situação do Diário"],
        "registros": [
            {"turma": "9º Ano A (EF)", "disciplina": "Matemática", "professor": "Prof. Carlos Eduardo", "aulas": "48 / 50", "media": "8,5", "situacao": "Fechado"},
            {"turma": "1ª Série B (EM)", "disciplina": "Língua Portuguesa", "professor": "Profa. Mariana Souza", "aulas": "46 / 48", "media": "8,2", "situacao": "Fechado"},
            {"turma": "2ª Série A (EM)", "disciplina": "Física", "professor": "Prof. Roberto Lima", "aulas": "39 / 40", "media": "7,9", "situacao": "Em Revisão"},
            {"turma": "3ª Série A (EM)", "disciplina": "História", "professor": "Profa. Fernanda Alves", "aulas": "40 / 40", "media": "8,8", "situacao": "Fechado"},
            {"turma": "7º Ano C (EF)", "disciplina": "Ciências", "professor": "Prof. Carlos Eduardo", "aulas": "44 / 44", "media": "8,6", "situacao": "Fechado"},
        ],
        "observacoes_pedagogicas": [
            "92,8% dos diários bimestrais já validados pelos docentes responsáveis.",
            "Turma 2ª Série A (Física) aguarda lançamento final das atividades de recuperação contínua.",
            "Dados sintéticos para demonstração pedagógica de acesso compartilhado (Professores / Gestão).",
        ],
    }


@app.get("/api/relatorios/auditoria-matriculas", tags=["Relatórios Pedagógicos"])
def get_relatorio_auditoria_matriculas(current_user: dict = Depends(get_current_user)):
    """
    #REL-03: Auditoria de Matrículas e Frequência Escolar.
    Classificação: Exclusivo Diretoria (perfil permitido: diretor).
    """
    report = authorize_report_access("auditoria-matriculas", current_user)
    return {
        "status": "autorizado",
        "relatorio": report,
        "consultado_por": {
            "nome": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
        },
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "resumo": {
            "matriculas_ativas": 486,
            "vagas_remanescentes": 18,
            "frequencia_global": "93,8%",
            "alertas_busca_ativa": 9,
        },
        "colunas": ["Segmento", "Matrículas Ativas", "Transferências", "Frequência Média", "Alertas Busca Ativa", "Conformidade SED"],
        "registros": [
            {"segmento": "Ensino Fundamental II (6º ao 9º)", "ativas": 244, "transferencias": 6, "frequencia": "94,5%", "busca_ativa": 4, "conformidade": "100% Regular"},
            {"segmento": "Ensino Médio Regular / Integral", "ativas": 242, "transferencias": 8, "frequencia": "93,1%", "busca_ativa": 5, "conformidade": "100% Regular"},
        ],
        "observacoes_pedagogicas": [
            "Auditoria mensal sincronizada com a Secretaria Escolar Digital (SED) sem pendências documentais.",
            "9 estudantes sinalizados para contato preventivo da Busca Ativa Escolar (frequência entre 76% e 81%).",
            "Relatório estritamente restrito à Diretoria (HTTP 403 automático para demais perfis).",
        ],
    }


@app.get("/auth/health", response_model=MessageResponse, tags=["Monitoramento"])
def health_check():
    """Healthcheck para monitorar o status do backend."""
    return {"message": "Serviço de autenticação online e operacional.", "success": True}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Autenticação"])
def register_user(data: UserRegisterRequest):
    """
    Registra um novo usuário no banco de dados.
    Verifica unicidade de e-mail e aplica hash seguro na senha.
    """
    email_clean = data.email.lower().strip()
    role_clean = data.role.lower().strip() if data.role else "professor"
    if role_clean == "diretoria":
        role_clean = "diretor"
    if role_clean not in ALLOWED_ROLES:
        role_clean = "professor"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"O e-mail '{email_clean}' já se encontra cadastrado no sistema."
            )

        hashed = hash_password(data.password)
        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO users (name, email, hashed_password, role, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (data.name.strip(), email_clean, hashed, role_clean, now_iso))
        conn.commit()

        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM users WHERE id = ?", (new_id,))
        new_user = cursor.fetchone()

        return {
            "id": new_user["id"],
            "name": new_user["name"],
            "email": new_user["email"],
            "role": new_user["role"],
            "is_active": bool(new_user["is_active"]),
            "created_at": new_user["created_at"]
        }


@app.post("/auth/login", response_model=TokenResponse, tags=["Autenticação"])
def login_json(credentials: UserLoginRequest):
    """
    Endpoint de login via JSON (utilizado pelo frontend).
    Aceita campos email/senha ou username/password.
    Retorna o token de acesso JWT e os dados do usuário.
    """
    identifier = credentials.email or credentials.username
    password = credentials.password or credentials.senha

    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe e-mail e senha para realizar o login."
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = find_user_by_identifier(cursor, identifier)

        if not user or not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas: e-mail ou senha incorretos."
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta conta de usuário foi desativada pelo administrador."
            )

        return build_token_response(user)


@app.post("/auth/token", response_model=TokenResponse, tags=["Autenticação"])
def login_oauth2_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint compatível com a especificação OAuth2 Password Flow.
    Permite autenticação direta pelo botão 'Authorize' da documentação Swagger (/docs).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = find_user_by_identifier(cursor, form_data.username)

        if not user or not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas: e-mail ou senha incorretos.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta conta de usuário foi desativada pelo administrador.",
            )

        return build_token_response(user)


@app.get("/auth/me", response_model=UserResponse, tags=["Autenticação"])
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Endpoint protegido: Retorna os dados do perfil do usuário atualmente autenticado.
    Requer o cabeçalho 'Authorization: Bearer <token>'.
    """
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user["role"],
        "is_active": bool(current_user["is_active"]),
        "created_at": current_user["created_at"]
    }


@app.post("/auth/logout", response_model=MessageResponse, tags=["Autenticação"])
def logout_user():
    """
    Endpoint de logout para encerramento de sessão do usuário.
    """
    return {"message": "Sessão finalizada com sucesso no servidor.", "success": True}


# ---------------------------------------------------------------------------
# INICIALIZAÇÃO DIRETA VIA PYTHON
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(" Escola do Futuro — EE Antonio Reginato")
    print(" Iniciando servidor FastAPI em http://127.0.0.1:8000")
    print(" Documentação Swagger: http://127.0.0.1:8000/docs")
    print(" Credenciais de teste:")
    print("   - Gestor:    gestor@escola.sp.gov.br    / gestor123")
    print("   - Professor: professor@escola.sp.gov.br / professor123")
    print("   - Diretor:   diretor@escola.sp.gov.br   / diretor123")
    print("   - Admin:     admin@escola.sp.gov.br     / admin123")
    print("=" * 60 + "\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
