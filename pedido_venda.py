'''
pedido_venda_produto

Estrutura do Pedido de Vendas de Produtos.

             cabecalho: Informações do cabeçalho do pedido.+         
                 frete: Dados da Aba "Frete e Outras Despesas" do Pedido de Venda.+
informacoes_adicionais:	Dados da Aba "Informações Adicionais" do Pedido de Venda.+
        codigo_parcela: Código da parcela/Condição de pagamento.+           
                   det: Dados da Aba "Itens da Venda" do Pedido de Venda.+
'''

'''
cabeçalho:
    codigo_pedido_integracao - 4338339994989
    codigo_cliente - cria lista + email cliente ok clientes.json
    data_previsao - hoje
    etapa - "10" - string -> "Pedido de Venda" | "50" - string -> "Faturar"
    codigo_parcela - criar lista ok
    codigo_cenario_impostos - 9553371106 - int

frete
    codigo_transportadora - criar lista
    modalidade - "0", "1" ou "9" / tempo de execução
    quantidade_volumes - tempo de execução
    valor_frete - tempo de execução

informacoes_adicionais
    codigo_categoria - "1.01.03" - string
    codigo_conta_corrente - 9520897830 - int
    numero_pedido_cliente - tempo de execução - string
    consumidor_final - "s"
    utilizar_emails - criar lista com email cliente ok clientes.json

não precisa    
lista_parcelas
    parcela - parcelamento: código da parcela
        endpoints
            consulta: https://app.omie.com.br/api/v1/geral/parcelas/ListarParcelas
            inclusão: https://app.omie.com.br/api/v1/geral/parcelas/IncluirParcela

det
    ide
        codigo_item_integracao - criar lista ok produtos.json
    produto
        codigo_produto - criar lista ok produtos.json
        quantidade - decimal
        valor_unitario - decimal            
'''