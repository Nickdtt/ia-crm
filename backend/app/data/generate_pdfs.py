"""
Script para gerar os PDFs fictícios da agência para o sistema RAG.
Baseado no documento de posicionamento real da "Isso não é uma agência".

Uso:
    cd backend
    python -m app.data.generate_pdfs
"""

from fpdf import FPDF
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "pdfs")


def create_pdf(filename: str, title: str, sections: list[tuple[str, str]]):
    """Cria um PDF com título e seções (subtítulo, conteúdo)."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # Título
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    
    # Subtítulo institucional
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Isso nao e uma agencia - Estudio de Crescimento Digital", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    
    for subtitle, content in sections:
        # Subtítulo da seção
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, subtitle, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        # Conteúdo
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, content)
        pdf.ln(4)
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    pdf.output(filepath)
    print(f"  Criado: {filepath}")


def generate_posicionamento():
    create_pdf("posicionamento.pdf", "Posicionamento e Forma de Apresentacao", [
        ("Quem Somos", 
         "A 'Isso nao e uma agencia' nao se posiciona como uma agencia tradicional de marketing. "
         "O nome ja comunica diferenciacao, e o discurso da empresa reforça que o foco nao esta na "
         "prestacao de servicos isolados, mas na construcao de sistemas previsiveis de crescimento.\n\n"
         "Somos um estudio de crescimento digital. Uma operacao de aquisicao de clientes. "
         "Um parceiro de crescimento digital. Consultoria em marketing e automacao. "
         "Time de crescimento sob demanda. Engenharia de crescimento."),
        
        ("Forma de Apresentacao",
         "A 'Isso nao e uma agencia' constroi sistemas que geram clientes de forma previsivel para "
         "empresas que querem crescer sem depender de tentativa e erro.\n\n"
         "Nos nao somos uma agencia de marketing. Nao vendemos posts, artes ou promessas vagas. "
         "Construimos sistemas de aquisicao e automacao que transformam marketing em um processo "
         "previsivel de geracao de clientes.\n\n"
         "Agencias vendem campanhas. Nos construimos maquinas de crescimento. Implementamos funis, "
         "automacoes e estrategias que trabalham todos os dias para gerar oportunidades, nutrir leads "
         "e transformar interesse em vendas."),
        
        ("Sistemas de Crescimento",
         "1. Sistema de Geracao de Leads: trafego pago + paginas de captura + oferta estrategica\n"
         "2. Sistema de Nutricao e Qualificacao: automacao, e-mail marketing, WhatsApp, CRM\n"
         "3. Sistema de Conversao em Vendas: funil de vendas, follow-up, scripts, otimizacao\n"
         "4. Sistema de Retencao e Recompra: remarketing + automacoes de fidelizacao"),
        
        ("Frases de Posicionamento",
         "- Nos nao rodamos campanhas. Construimos ativos de marketing.\n"
         "- Substituimos tentativa e erro por processo e previsibilidade.\n"
         "- Marketing deixa de ser custo e vira sistema de aquisicao.\n"
         "- Nao entregamos posts. Entregamos crescimento mensuravel.\n"
         "- Sua empresa nao precisa de mais marketing. Precisa de um sistema que traga clientes.\n\n"
         "Pitch de 10 segundos: A gente nao e uma agencia. A gente estrutura todo o sistema digital "
         "que faz empresas atrairem, nutrirem e fecharem clientes no automatico."),
    ])


def generate_tabela_servicos():
    create_pdf("tabela_servicos.pdf", "Tabela de Servicos e Investimentos", [
        ("Consultoria Inicial (Gratuita)",
         "Reuniao online de 40 minutos via Google Meet para entender o momento do seu negocio, "
         "seus objetivos e desafios. Sem compromisso. Analisamos juntos se faz sentido trabalhar "
         "juntos e qual seria o melhor caminho.\n\n"
         "Investimento: Gratuito\n"
         "Duracao: 40 minutos\n"
         "Formato: Google Meet"),
        
        ("Plano Essencial - Sistema de Geracao de Leads",
         "Ideal para empresas que precisam comecar a gerar leads qualificados de forma previsivel.\n\n"
         "Inclui:\n"
         "- Gestao de trafego pago (Google Ads + Meta Ads)\n"
         "- Criacao de 2 paginas de captura otimizadas\n"
         "- Configuracao de funil basico de conversao\n"
         "- Relatorios mensais de performance\n"
         "- Reuniao mensal de alinhamento\n\n"
         "Investimento: a partir de R$ 3.000/mes\n"
         "Contrato minimo: 3 meses\n"
         "Setup inicial: R$ 1.500 (cobrado apenas no primeiro mes)"),
        
        ("Plano Crescimento - Sistema Completo de Aquisicao",
         "Para empresas que querem um sistema completo: da atracao ate a conversao em vendas.\n\n"
         "Inclui tudo do Plano Essencial, mais:\n"
         "- Automacao de e-mail marketing (sequencias de nutricao)\n"
         "- Integracao com CRM\n"
         "- Automacao de WhatsApp para follow-up\n"
         "- Criacao de conteudo estrategico (4 posts/semana)\n"
         "- Dashboard de metricas em tempo real\n"
         "- Reunioes quinzenais de estrategia\n\n"
         "Investimento: a partir de R$ 5.500/mes\n"
         "Contrato minimo: 6 meses\n"
         "Setup inicial: R$ 2.500"),
        
        ("Plano Aceleracao - Engenharia de Crescimento",
         "Nosso plano mais completo. Time dedicado atuando como seu departamento de marketing.\n\n"
         "Inclui tudo do Plano Crescimento, mais:\n"
         "- Gestao completa de redes sociais (Instagram, LinkedIn, TikTok)\n"
         "- Producao de video (Reels, Stories, YouTube Shorts)\n"
         "- SEO tecnico e producao de conteudo para blog\n"
         "- Estrategia de remarketing avancado\n"
         "- Treinamento da equipe comercial\n"
         "- Reunioes semanais + suporte prioritario\n\n"
         "Investimento: a partir de R$ 10.000/mes\n"
         "Contrato minimo: 6 meses\n"
         "Setup inicial: R$ 4.000"),
        
        ("Servicos Avulsos",
         "- Criacao de site institucional: a partir de R$ 4.500\n"
         "- Landing page de conversao: a partir de R$ 1.800\n"
         "- E-commerce completo: a partir de R$ 12.000\n"
         "- Consultoria estrategica (pontual): R$ 500/hora\n"
         "- Auditoria de marketing digital: R$ 2.500\n"
         "- Treinamento de equipe (workshop): R$ 3.000/dia"),
    ])


def generate_cases_sucesso():
    create_pdf("cases_sucesso.pdf", "Cases de Sucesso", [
        ("Case 1: Clinica Odontologica Sorriso Perfeito - Salvador/BA",
         "Segmento: Clinica Odontologica\n"
         "Desafio: A clinica dependia exclusivamente de indicacoes e tinha agenda vazia "
         "3 dias por semana. Investiam R$ 800/mes em posts no Instagram sem retorno mensuravel.\n\n"
         "Solucao implementada:\n"
         "- Sistema de Geracao de Leads com Google Ads focado em implantes e ortodontia\n"
         "- Landing pages especificas por procedimento\n"
         "- Automacao de WhatsApp para agendamento\n"
         "- Funil de nutricao por e-mail para pacientes inativos\n\n"
         "Resultados em 6 meses:\n"
         "- 340% de aumento em agendamentos online\n"
         "- Custo por lead reduzido de R$ 85 para R$ 22\n"
         "- Agenda 95% preenchida (era 60%)\n"
         "- ROI de 8.2x sobre o investimento em marketing\n"
         "- Faturamento cresceu 180%\n\n"
         "Investimento mensal do cliente: R$ 5.500/mes (Plano Crescimento)"),
        
        ("Case 2: Dr. Ricardo Mendes - Dermatologista - Salvador/BA",
         "Segmento: Medico Autonomo (Dermatologia)\n"
         "Desafio: Profissional renomado mas sem presenca digital. Perdia pacientes para "
         "concorrentes com forte marketing online. Zero seguidores no Instagram.\n\n"
         "Solucao implementada:\n"
         "- Gestao completa de Instagram (conteudo educativo + Reels)\n"
         "- Google Ads para 'dermatologista Salvador'\n"
         "- Sistema de agendamento online integrado\n"
         "- Estrategia de autoridade com artigos no blog\n\n"
         "Resultados em 4 meses:\n"
         "- De 0 para 12.000 seguidores no Instagram\n"
         "- 45 novos pacientes/mes vindos do digital\n"
         "- Posicao #1 no Google para 'dermatologista Salvador'\n"
         "- Lista de espera de 3 semanas para consultas\n\n"
         "Investimento mensal do cliente: R$ 10.000/mes (Plano Aceleracao)"),
        
        ("Case 3: Farmacia Vida Natural - Rede com 3 unidades - BA",
         "Segmento: Farmacia / E-commerce Saude\n"
         "Desafio: Concorrencia com grandes redes. Vendas online representavam apenas 5% do "
         "faturamento. Sem estrategia digital estruturada.\n\n"
         "Solucao implementada:\n"
         "- E-commerce completo com catalogo de 2.000 produtos\n"
         "- Campanha de trafego pago focada em manipulados e naturais\n"
         "- Sistema de remarketing para carrinho abandonado\n"
         "- Automacao de recompra (lembretes de medicamentos)\n"
         "- Programa de fidelidade digital\n\n"
         "Resultados em 8 meses:\n"
         "- Vendas online passaram de 5% para 35% do faturamento\n"
         "- Ticket medio online 40% maior que na loja fisica\n"
         "- 2.800 clientes cadastrados na base digital\n"
         "- Reducao de 60% no custo de aquisicao de clientes\n\n"
         "Investimento mensal do cliente: R$ 8.000/mes (Plano customizado)"),
        
        ("Case 4: PsicoVida - Clinica de Psicologia - Feira de Santana/BA",
         "Segmento: Psicologo\n"
         "Desafio: Dificuldade em atrair pacientes para terapia online. Concorrencia crescente "
         "de plataformas como Zenklub e Vittude.\n\n"
         "Solucao implementada:\n"
         "- Conteudo educativo sobre saude mental (Instagram + Blog)\n"
         "- Google Ads segmentado por tipo de terapia\n"
         "- Landing page com agendamento direto\n"
         "- Sequencia de e-mails para leads que nao agendaram\n\n"
         "Resultados em 5 meses:\n"
         "- 28 novos pacientes/mes (era 6)\n"
         "- 70% dos pacientes vieram do Google\n"
         "- Taxa de conversao da landing page: 12%\n"
         "- Expansao para 2 novos psicologos na equipe\n\n"
         "Investimento mensal do cliente: R$ 3.500/mes (Plano Essencial + complementos)"),
    ])


def generate_faq():
    create_pdf("faq_servicos.pdf", "Perguntas Frequentes (FAQ)", [
        ("Como funciona o processo de trabalho?",
         "Tudo comeca com uma consultoria gratuita de 40 minutos onde entendemos seu negocio, "
         "seus objetivos e desafios. A partir dai, montamos uma proposta personalizada com o "
         "plano mais adequado. Apos aprovacao, iniciamos o setup (7-15 dias uteis) e em seguida "
         "comecam as campanhas e automacoes. Voce recebe relatorios periodicos e tem reunioes "
         "regulares de alinhamento."),
        
        ("Qual o investimento minimo?",
         "Nosso plano mais acessivel, o Plano Essencial, comeca em R$ 3.000/mes. "
         "Este valor inclui gestao de trafego pago, paginas de captura e funil basico. "
         "Importante: este valor e o investimento na nossa gestao. O budget de midia "
         "(valor investido nas plataformas de anuncio) e separado e definido juntos "
         "de acordo com seus objetivos. Recomendamos um minimo de R$ 1.500/mes em midia."),
        
        ("Quanto tempo leva para ver resultados?",
         "Resultados iniciais (primeiros leads) costumam aparecer nas primeiras 2-4 semanas "
         "apos o lancamento das campanhas. Resultados consistentes e otimizados geralmente "
         "se consolidam entre o 2o e 3o mes. Projetos de SEO e conteudo tem um prazo maior: "
         "3-6 meses para resultados significativos. Cada negocio tem seu ritmo, e trabalhamos "
         "com transparencia total sobre expectativas."),
        
        ("Voces atendem apenas o segmento de saude?",
         "Nosso foco principal e o segmento de saude e bem-estar: clinicas medicas, odontologicas, "
         "esteticas, profissionais autonomos da saude, farmacias e e-commerces de saude. "
         "Nos especializamos neste mercado porque entendemos as regulamentacoes (CFM, CRO), "
         "as particularidades de comunicacao e o comportamento do paciente/cliente. "
         "Eventualmente atendemos outros segmentos quando faz sentido estrategico."),
        
        ("Qual a diferenca de voces para uma agencia tradicional?",
         "Agencias tradicionais vendem servicos isolados: posts, artes, gerenciamento de redes. "
         "Nos construimos sistemas completos de aquisicao de clientes. A diferenca e que um post "
         "bonito nao garante resultado. Um sistema de geracao de leads, com funil, automacao e "
         "otimizacao continua, gera resultados previsiveis e escalaveis. Nos nao entregamos posts. "
         "Entregamos crescimento mensuravel."),
        
        ("Preciso ter um site para comecar?",
         "Nao necessariamente. Podemos comecar com landing pages especificas enquanto desenvolvemos "
         "seu site completo. Inclusive, em muitos casos, landing pages focadas convertem melhor que "
         "sites institucionais tradicionais. Se voce ja tem um site, fazemos uma auditoria para "
         "identificar oportunidades de melhoria."),
        
        ("Como funciona o contrato?",
         "Trabalhamos com contratos de 3 ou 6 meses, dependendo do plano escolhido. "
         "Isso porque marketing digital exige tempo para otimizacao e maturacao. "
         "Resultados sustentaveis nao acontecem da noite pro dia. Apos o periodo minimo, "
         "o contrato renova automaticamente com aviso previo de 30 dias para cancelamento."),
        
        ("Voces garantem resultados?",
         "Nao fazemos promessas irreais. O que garantimos e: estrategia profissional, "
         "execucao de qualidade, transparencia total nos dados e otimizacao continua. "
         "Nossos cases mostram resultados concretos, mas cada negocio e unico. "
         "Trabalhamos com metas realistas definidas juntos na consultoria inicial."),
    ])


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Gerando PDFs da agencia ficticia...")
    generate_posicionamento()
    generate_tabela_servicos()
    generate_cases_sucesso()
    generate_faq()
    print(f"\n✅ {len(os.listdir(OUTPUT_DIR))} PDFs gerados em {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
