"""
Mensagens padronizadas reutilizadas pelo Router, Validator e nodes.
Centraliza todo o texto enviado ao cliente para facilitar manutenção.
"""


def exit_message(first_name: str = "") -> str:
    nome = f" {first_name}" if first_name else ""
    return (
        f"Tudo bem{nome}! 😊 Sem pressão nenhuma.\n\n"
        f"Se em algum momento quiser conversar sobre como estruturar a captação de clientes "
        f"da sua clínica, pode nos chamar. Até mais! 👋"
    )


def out_of_scope_message() -> str:
    return (
        "Olá! 😊 Parece que você está buscando atendimento como paciente.\n\n"
        "A Isso não é uma agência atende donos de clínicas e profissionais de saúde "
        "que querem captar mais pacientes com marketing digital.\n\n"
        "Se você tiver um negócio na área da saúde e precisar de ajuda com marketing, "
        "pode nos chamar! 🙏"
    )


def human_escalation_message(first_name: str = "") -> str:
    nome = f" {first_name}" if first_name else ""
    return (
        f"Entendo{nome}! 😊 Vou encaminhar você para um atendente da nossa equipe.\n\n"
        f"Alguém vai entrar em contato em breve por aqui mesmo. Aguarde um momento! 🙏"
    )


def off_topic_message(first_name: str = "", current_question: str = "") -> str:
    nome = f", {first_name}" if first_name else ""
    if current_question:
        return f"Entendido{nome}! 😄 Continuando — {current_question}"
    return f"Haha{nome}! 😄 Continuando de onde paramos..."


def question_transition_message(first_name: str = "") -> str:
    nome = f", {first_name}" if first_name else ""
    return f"Boa pergunta{nome}! Deixa eu responder isso..."


def reschedule_message(first_name: str = "") -> str:
    nome = f", {first_name}" if first_name else ""
    return f"Claro{nome}! Vamos escolher outro horário. Qual data e horário prefere?"


def clarification_message(first_name: str = "", retry_count: int = 1) -> str:
    nome = f", {first_name}" if first_name else ""
    return (
        f"Desculpa{nome}, não consegui entender direito 😅\n\n"
        f"Como posso te ajudar? Escolha uma opção:\n\n"
        f"1️⃣ Quero agendar uma reunião\n"
        f"2️⃣ Tenho uma dúvida sobre os serviços\n"
        f"3️⃣ Outro assunto"
    )
