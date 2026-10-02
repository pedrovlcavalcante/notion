import logging
import os
import subprocess
from pre_notacp import PreNota  # Assumindo que a classe PreNota está em prenota.py

# Configuração do Logger para salvar o histórico de pedidos gerados
logging.basicConfig(
    filename="historico_pedidos.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)


def limpar_tela_e_exibir_cabecalho():
    """Limpa o terminal e exibe o cabeçalho fixo do sistema."""
    comando = "cls" if os.name == "nt" else "clear"
    subprocess.run(comando, shell=True)

    print("=" * 60)
    print(f"{'SISTEMA DE PRÉ-NOTAS 2.0':^60}")
    print("=" * 60)
    print()

def registrar_log_pedido(pedido: PreNota, status: str):
    """Grava no arquivo historico_pedidos.log todas as informações exibidas na tela."""
    mod_map = {"0": "CIF", "1": "FOB", "9": "SEM FRETE"}
    mod_desc = mod_map.get(str(pedido.mod_frete), "N/A")

    log_entry = (
        f"\n[{status}] REGISTRO DE PEDIDO: {pedido.numero}\n"
        f"  - Cliente: {pedido.cliente.nome}\n"
        f"  - Vendedor: {pedido.vendedor}\n"
        f"  - Pagamento: {pedido.condicao_pagamento}\n"
        f"  - Transportadora: {pedido.transportadora}\n"
        f"  - Tabela: {pedido.tabela_mercos}\n"
        f"  - Modalidade Frete: {mod_desc}\n"
        f"  - Volumes: {pedido.volumes}\n"
        f"  - Frete Tabelado: R$ {pedido.frete_tabelado:,.2f}\n"
        f"  - Cotação: R$ {pedido.valor_cotacao:,.2f}\n"
        f"  - Frete NOTA: R$ {pedido.frete_nota:,.2f}\n"
        f"  - Valor Pedido: R$ {pedido.valor_pedido:,.2f}\n"
        f"  - Valor NF: R$ {pedido.valor_nf:,.2f}\n"
        f"  - Porcentagem: {pedido.pct_faturamento * 100:.1f}%\n"
        f"{'-' * 60}"
    )

    logging.info(log_entry)

def interagir_com_usuario():
    # print("=" * 50)
    # print(f"{'SISTEMA DE FATURAMENTO E PRÉ-NOTA OMIE':^50}")
    # print("=" * 50)

    # 1. Entrada do Número do Pedido
    numero_pedido = input("\nDigite o número do pedido Mercus ou 0 para encerrar: ").strip()
    if not numero_pedido or numero_pedido == "0":
        print("Número de pedido inválido. Encerrando.")
        return False

    # 2. Verificação/Download do HTML via Selenium
    # path_html = Path("pedidos") / f"{numero_pedido}.html"
    print(f"\n[+] Baixando HTML do Mercus...")
    sucesso = PreNota.baixar_html_mercus(numero_pedido)
    if not sucesso:
        print("❌ Falha ao obter a página do pedido no Mercus. Encerrando.")
        return

    # 3. Instanciação da PreNota (executa o parsing herdado de Pedido)
    print("\n[+] Lendo e extraindo dados do pedido...")
    pedido = PreNota(numero_pedido)
    pedido.extrai_produtos()
    
    pedido.itens_fabrica()
    pedido.calcula_frete_tabelado()
    pedido.calcular_ajustes_faturamento()

    print(f"✓ Cliente: {pedido.cliente.nome}")
    print(f"✓ Destino: {pedido.cliente.cidade}/{pedido.cliente.estado}")
    print(f"✓ Valor Original do Pedido: R$ {pedido.valor_pedido:,.2f}")
    print(f"✓ Tabela Mercos: {pedido.tabela_mercos}")
    print(f"✓ Porcentagem: {pedido.porcentagem}%")
    print(f"✓ Transportadora: {pedido.transportadora}")
    print(f"✓ Frete Tabelado: R$ {pedido.frete_tabelado:,.2f}")
    print(f"✓ Frete a Pagar: R$ {pedido.frete_nota:,.2f}")
    print(f"✓ Vendedor: {pedido.vendedor}")
    print(f"✓ Observação Interna: {pedido.observacao_interna}")
    print(f"✓ Informações adicionais: {pedido.informacoes_adicionais}")

    # 4. Mapeamento de Códigos (Cliente, Transportadora, Produtos)
    # Se faltar algum produto substituto, o próprio método solicita via input
    print("\n[+] Mapeando códigos com Omie...")
    pedido.mapear_codigos_locais()

    # 5. Coleta de Informações de Faturamento e Frete
    print("\n" + "-" * 50)
    print(" INFORME OS DADOS DE FATURAMENTO E FRETE")
    print("-" * 50)

    # Porcentagem de faturamento
    pct_padrao = pedido.porcentagem if pedido.porcentagem else "20"
    pct_input = input(
        f"• Porcentagem de nota (%)[Padrão: {pct_padrao}%]: "
    ).strip()

    # Modalidade de frete
    print("\nModalidades de Frete disponíveis:")
    print("  0 - CIF (Frete por conta do Emitente)")
    print("  1 - FOB (Frete por conta do Destinatário)")
    print("  9 - Sem Frete (Retirada / Sem cobrança na Nota)")

    mod_frete = (
        input("• Escolha a modalidade de frete [Padrão 9]: ").strip() or "9"
    )

    valor_cotacao = 0.0
    volumes = 1
    peso_bruto = 0.0

    v_vol = input("• Quantidade de Volumes [Padrão 1]: ").strip()
    volumes = int(v_vol) if v_vol else 1

    # Solcita cotação/volumes apenas se houver frete
    if mod_frete != "9":
        v_cot = (
            input("• Valor da Cotação do Frete (R$): ")
            .strip()
            .replace(",", ".")
        )
        valor_cotacao = float(v_cot) if v_cot else 0.0


        v_peso = (
            input("• Peso Bruto em Kg [Padrão 0.0]: ")
            .strip()
            .replace(",", ".")
        )
        peso_bruto = float(v_peso) if v_peso else 0.0

    # 6. Aplicação de Regras de Negócio e Cálculos
    pedido.calcular_ajustes_faturamento(
        pct_input=pct_input,
        mod_frete=mod_frete,
        volumes=volumes,
        valor_cotacao=valor_cotacao,
        peso_bruto=peso_bruto,
    )
    # 7. Exibição do Resumo
    print("\n")
    pedido.exibir_painel_informativo()

    # 8. Confirmação do Usuário para Envio
    confirmar = (
        input(
            "\n👉 Deseja enviar esta Pré-Nota para a Omie e atualizar o Notion? (S/N): "
        )
        .strip()
        .upper()
    )

    if confirmar == "S":
        print("\n[+] Deletando pré-nota anterior no Omie (caso exista)...")
        pedido.deletar_prenota_omie()

        print("[+] Cadastrando/Enviando nova pré-nota para a Omie...")
        if pedido.enviar_prenota_omie():
            print("[+] Sincronizando dados com o Notion...")
            pedido.sincronizar_notion()
            print("\n✅ Processo concluído com sucesso!")
            registrar_log_pedido(pedido, status="SUCESSO / ENVIADO")
        else:
            print("\n❌ Ocorreu um erro ao enviar para a Omie.")
            registrar_log_pedido(pedido, status="ERRO / ENVIAR OMIE")
    else:
        print("\n⚠️ Operação cancelada. Nenhuma alteração foi enviada.")
        registrar_log_pedido(pedido, status="CANCELADO PELO USUARIO")
    input("Pressione Enter para continuar")
    return True

if __name__ == "__main__":
    continua = True
    while continua:
        limpar_tela_e_exibir_cabecalho()
        continua = interagir_com_usuario()