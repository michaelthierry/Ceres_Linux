# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Ceres
                                 A QGIS plugin
 Automação de Cálculo NDVI
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-09-29
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Michael Thierry da Silva
        email                : michaelthierry86@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import (
    QAction,
    QFileDialog
)

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .ceres_dialog import CeresDialog
import os.path

# Minhas importações
from qgis.gui   import QgsMessageBar
from qgis.core  import(
    Qgis,
    QgsApplication,
    QgsProject,
    QgsVectorLayer,
    QgsRasterBandStats,
    QgsColorRampShader, 
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterPipe,
    QgsRasterFileWriter,
    QgsVectorFileWriter
)
from PyQt5.QtCore   import QUrl, QTimer
from PyQt5.QtGui    import QDesktopServices
from datetime       import datetime, date
import json
import requests
#import pandas as  dataframe
import processing
import ast


URL_AUTH = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
URL_CREATE_COUNT = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/login-actions/registration?client_id=cdse-public&tab_id=996ti_TWJXI"

class Ceres:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Ceres_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Ceres')
        # 
        self.user = None
        self.token = None
        self.mensagens = QgsMessageBar()

        # Tenta pegar o arquivo de usuarios onde tem as credenciais
        try:
            with open(self.plugin_dir+'/config.json', 'r') as credenciais:
                self.user = json.load(credenciais)
                credenciais.close()
            
        except:
            print("Erro ao carregar credenciais do arquivo")

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Ceres', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/ceres/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Ceres'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Ceres'),
                action)
            self.iface.removeToolBarIcon(action)
    
    """
    +---------------------------------------------+
    | METODOS UTILIZADO PARA AS TAREFAS DO PLUGIN |
    +---------------------------------------------+
    """
    """
        # METODOS PARA LOGIN, LEMBRE-ME E CADASTRO NO COPERNICUS
    """
    def login(self):
        """
        Este método é responsavel por validar o cadastro do usuario no sistema copernicus
        e obter o token de acesso como o qual ele poderá obter o produtos (pacotes de imagens do mesmo)
        """

        # Pega usuario e senha das caixas de edição
        #self.usuario = self.dlg.lineEdit_5.text().strip()
        #self.senha = self.dlg.mLineEdit.text().strip()

        # Automatizando preenchimento de senha e login
        self.usuario = self.user["user"]["login"]
        self.senha = self.user["user"]["pass"]

        # tenta fazer conexão
        try:
            self.token = self.pegar_token(self.usuario, self.senha)
            # se o token estiver ok
            if self.token is not None:
                # exibe mensagem
                self.pop_up(3, "Acesso Autorizado!", 3)
                # ativa a tabela de parametros
                self.dlg.tabWidget.setTabEnabled(1, True)
            else:
                self.pop_up(1, "Senha ou usuário incorretos", 5)
        except Exception as e:
            self.pop_up(1, "Senha ou usuário incorretos", 5)

    def pegar_token(self, usuario, senha):
        """
            # Metodo para obter o token de acesso ao copernicus e seus recursos e serviços 
        """
        # criando conjunto de dados
        dados = {
            "client_id": "cdse-public",
            "username": usuario,
            "password": senha,
            "grant_type": "password"
        }

        # tentando obter o token
        try:
            resposta = requests.post(URL_AUTH, data=dados)
            resposta.raise_for_status()
            return resposta.json()["access_token"]
        except Exception as e:
            raise Exception(f"Falha ao criar o token de acesso. Resposta de servidor {resposta.json()}")

    def pop_up(self, codigo, mensagem, tempo):
        # de acordo com o codigo é exibida uma determinada mensagem e tempo
        if codigo == 0:
            self.mensagens.clearWidgets()
            self.mensagens.pushMessage(mensagem, level=Qgis.Info, duration=tempo)
            QgsApplication.processEvents()
        elif codigo == 1:
            self.mensagens.clearWidgets()
            self.mensagens.pushMessage(mensagem, level=Qgis.Warning, duration=tempo)
            QgsApplication.processEvents()
        elif codigo == 2:
            self.mensagens.clearWidgets()
            self.mensagens.pushMessage(mensagem, level=Qgis.Critical, duration=tempo)
            QgsApplication.processEvents()
        elif codigo == 3:
            self.mensagens.clearWidgets()
            self.mensagens.pushMessage(mensagem, level=Qgis.Success, duration=tempo)
            QgsApplication.processEvents()
        else:
            print("Erro: Código invalido")

    def abir_site_copernicus(self):
        url = QUrl(URL_CREATE_COUNT)
        QDesktopServices.openUrl(url)

    """
        # METODOS PARA DOWNLOAD DOS PRODUTOS DO COPERNICUS POR MEIO DE UM PRODUTO PASSADO. 
    """
    def download(self):
        """
        - pega as coordendas
        - pega os ids
        - cria requisição
        - faz download da banda
        """
        try:
            # pegando o caminho do shape file pela linha de edição e removendo espaços se houver e verifica se o caminho
            caminhoArquivo = self.dlg.lineEdit.text().replace(" ", "")
            # se o caminho for fazio ou shape nenhum shape foi carregado
            if caminhoArquivo != "" and os.path.isfile(caminhoArquivo):
                # automatico
                # caminhoArquivo = self.user["rotas"]["shape"]

                # tenta pegar as datas 
                data = self.pegar_datas()

                # se a data não for nula
                if data is not None:
                    # adiciona o vetor no Layer principal do Qgis com nome de "Shape" Recupera o shape pelo caminho 
                    self.iface.addVectorLayer(caminhoArquivo, "Shape", "ogr")
                    shape = QgsProject.instance().mapLayersByName("Shape")[0]   
                    layer = QgsVectorLayer(caminhoArquivo, "Shape", "ogr")
                    # se o layer for fazio então nenhum shape foi carregado 
                    if layer is None:
                        self.pop_up(2, "Crítico: Shape não encontrado.", 5)
                    else:
                        # pega as coordenada e retorna as string do poligono e pega os produtos no periodo
                        poligono = self.pegar_coordenadas(layer)
                        idProdutos = self.pegar_ids_produtos(poligono, data)
                        # pegar ids do produtos
                        if len(idProdutos) == 0:
                            self.pop_up(2, "Erro: Não há produtos para o intervalos em específico", 5)
                        else:
                            # pega a data atual
                            dataAtual = str(date.today())
                            # caminho onde os downloads ficaram
                            caminho = os.environ.get("HOME") + "/Downloads/NDVI/" + f"{dataAtual}"
                            # criando cabeçalho
                            header = {
                                "Authorization": f"Bearer {self.token}",
                                "Content-Type": "application/json",
                            }
                            # criando a session
                            secao = requests.Session()
                            # atualizando o cabecalho
                            secao.headers.update(header)
                            # inicializando o download
                            for indice in range(len(idProdutos)):
                                # exibe mesagem de download
                                self.mensagens.pushMessage(
                                    f"Aviso: download...{indice+1}/{len(idProdutos)}",
                                    level=Qgis.Warning,
                                    duration=5
                                )
                                QgsApplication.processEvents()
                                # pega o nome dos produtos e as querys
                                nomes, querys = self.criar_requisicao_download(idProdutos[indice])
                                # para cada query faz o download das bandas em especifico
                                for query in range(len(querys)):
                                    # tenta fazer os downloads 
                                    try:
                                        self.download_banda(caminho, secao, querys[query], nomes[query])
                                    except Exception as e:
                                        print(f"Erro:{e}")
                            # limpando a janela    
                            self.mensagens.clearWidgets()
                            # exibindo a mensagem
                            self.mensagens.pushMessage(
                                "Info: download concluido",
                                level=Qgis.Info,
                                duration=5
                            )
                            QgsApplication.processEvents()
                            self.dlg.label_8.setText(caminho)
                            
                else:
                    print("Erro: de data")
            else:
                # Exibe um mensagem ao usuário
                self.pop_up(2, "Erro: nenhum shapefile foi passado ou o arquivo é invalido", 2)
        except Exception as e:
            print(f"Erro: {e}")
    
    def carregar_shape_file(self):
        """
        # Ao clicar no botão ao lado do campo do shapefile o usuário pode buscar um shape file no seu diretório 
        """
        # limpa a linha de edição do caminho do shapefile
        self.dlg.lineEdit.clear()
        shape = QFileDialog.getOpenFileName(self.dlg, "Select input file", "", "*.shp")
        self.dlg.lineEdit.setText(shape[0])

    def pegar_coordenadas(self, shape):
        # Pega os pontos as coordenadas do shapefile e retorna as coordenadas do poligono
        try:
            # Pegando as coordenadas do shape file
            xMin = shape.extent().xMinimum()
            xMax = shape.extent().xMaximum()
            yMin = shape.extent().yMinimum()
            yMax = shape.extent().yMaximum()

            # criando os pontos
            ponto1 = "{:.2f} {:.2f}".format(xMax, yMin)
            ponto2 = "{:.2f} {:.2f}".format(xMin, yMin)
            ponto3 = "{:.2f} {:.2f}".format(xMin, yMax)
            ponto4 = "{:.2f} {:.2f}".format(xMax, yMax)

            # criando o poligono
            poligono = "POLYGON(({}, {}, {}, {}, {}))".format(ponto1, ponto2, ponto3, ponto4, ponto1)
            
            # retorna poligono
            return poligono
                           
        except Exception as e:
            print(f"Erro:{e}")
            self.pop_up(2, "Houve um  erro ao pegar as coordenadas", 5)
            return None
    
    def pegar_datas(self):
        # tenta pegar as datas
        try:
            # lê os campos de edição
            dataInicial = self.dlg.dateEdit.text().replace("/", "-")
            dataFinal = self.dlg.dateEdit_2.text().replace("/", "-")
            # dividindo a tada em dia, mes e ano
            dia, mes, ano = dataInicial.split('-')
            dia1, mes1, ano1 = dataFinal.split('-')
            # formatado as datas
            dataInicial = f"{ano}-{mes}-{dia}"
            dataFinal = f"{ano1}-{mes1}-{dia1}"
            # convertendo para objetos do tipo data
            formato = "%Y-%m-%d"
            data1 = datetime.strptime(dataInicial, formato)
            data2 = datetime.strptime(dataFinal, formato)
            # comparando as datas 
            if data1 >= data2: 
                self.pop_up(2, "Erro: intervalo de datas inválido, data inicial maior ou igual que data final", 5)
                return None
            elif data1 < data2:
                data = [dataInicial, dataFinal]
                return data
        except Exception as e:
            self.pop_up(2, "Erro: ao pegar as datas", 3)
            return None

    def pegar_ids_produtos(self, coordenadas, data):
        # Atributos que desejamos que os produtos atendam (productType = 'S2MSI2A')
        atributosImagem = "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')"
        # A area de interesse que desejamos pegar
        regiaoPoligono = f"OData.CSC.Intersects(area=geography'SRID=4326;{coordenadas}')"
        # O periodo temporal do qual desejamos pegar a imagem
        intervaloTempo = f"ContentDate/Start gt {data[0]}T00:00:00.000Z and ContentDate/Start lt {data[1]}T00:00:00.000Z"
        # criando o filtro
        filtro = f"filter=Collection/Name eq 'SENTINEL-2' and {regiaoPoligono} and {atributosImagem} and {intervaloTempo}"
        # criando requisição de produtos
        requisicao = (
            f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?${filtro}"
        )
        # cria um dataframe
        identificadores = []
        # tenta
        try:
            # Obter as resposta da requisição
            resposta = requests.get(requisicao).json()
            # Pegando identifcares 
            identificadores = [item["Id"] for item in resposta["value"]]
            # retornando 
            return identificadores
        except Exception as e:
            # lança excessão
            print("Erro:", e)
            # retona os identificares vazios
            return identificadores
        
    def criar_requisicao_download(self, idProduto):
        # procurando  o id do nó interno
        url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({idProduto})/Nodes"
        json = requests.get(url).json()
        idInterno = json['result'][0]['Id']
        # procurando pelo nome interno do produto
        url = url + f"({idInterno})/Nodes(GRANULE)/Nodes"
        json = requests.get(url).json()
        idNome = json['result'][0]['Id']
        # pegando todos os produtos da pasta com resolução de 10 metros
        url = url + f"({idNome})/Nodes(IMG_DATA)/Nodes(R10m)/Nodes"
        json = requests.get(url).json()
        # pegando o nome das bandas
        banda4 = json['result'][3]['Id']
        banda8 = json['result'][4]['Id']
        # criando as querys
        queryBanda4 = url + f"({banda4})/$value"
        queryBanda8 = url + f"({banda8})/$value"
        querys = (queryBanda4, queryBanda8)
        #criando o nome dos arquivos (adicionando apenas a extensão rsrsrs)
        nomes = [banda4, banda8]
        # retornando os nomes
        return nomes, querys

    def download_banda(self, caminho, secao, requisicao, nome):
        '''
        # Faz o download das bandas dos produtos encontrados
        # Argumentos:
        #   caminho: onde o download deve ser feito
        #   secao: credenciais utilizadas para fazer o download dos produtos
        #   requisição: produtos escolhidos para download
        #   nome: nome dos pordutos a serem baixados 
        '''
        
        # verifica tenta obter os produtos
        try:
            # pega a resposta de autorização
            resposta = secao.get(requisicao, stream=True)
            # verifica a resposta
            if(resposta.status_code == 200):
                # cria a pasta se não existir e o local onde o arquivo será salvo
                os.makedirs(caminho, exist_ok=True)
                caminho_total = caminho + f'/{nome}'
                # tenta fazer o donwload dos produtos
                try:
                    with open(caminho_total, 'wb') as arquivo:
                        for chunk in resposta.iter_content(chunk_size=8192):
                            if chunk:
                                arquivo.write(chunk)
                        print(f"Download completo:{nome}")
                except Exception as e:
                    print(f'Erro:{e}')
            else:
                print(f'Erro:{resposta.status_code} - {resposta.text}')

        except Exception as e:
            # Abre um popup exibindo o erro
            print("Erro:", e)

    """
        # METODOS PARA CARREGAR BANDAS
    """
    def carrega_banda_4(self):
        self.dlg.lineEdit_2.clear()
        raster = QFileDialog.getOpenFileName(self.dlg, "Select input file", "", "*.jp2")
        self.dlg.lineEdit_2.setText(raster[0])

    def carrega_banda_8(self):
        self.dlg.lineEdit_3.clear()
        raster = QFileDialog.getOpenFileName(self.dlg, "Select input file", "", "*.jp2")
        self.dlg.lineEdit_3.setText(raster[0])

    """
        # METODO PARA GERAR MAPAS NDVI E SUAS ESTATÍSTICAS
    """

    def gerar_mapa_ndvi(self):
        '''
        # Essa função pega: o shapefile, banda 4 e banda 8.
        # Recorta as bandas de acordo com a forma do shapefile
        # Gera o mapa NDVI e o colore
        # Gera as estatisticas
        '''
        # tenta carregar o shape file
        try:
            shapePath = self.dlg.lineEdit.text()
            # verifica o shapefile
            if shapePath is None or shapePath == "":
                self.pop_up(2, "Erro: Nenhum arquivo Shapefile selecionado.", 2)
            else:
                # Tenta carregar o banda 4
                try:
                    # verifica a banda 4
                    banda4Path = self.dlg.lineEdit_2.text()
                    if banda4Path is None or banda4Path == "":
                        self.pop_up(2, "Erro: Nenhum arquivo JP2 selecionado no Banda A", 2)
                    else:
                        # tenta carregar bando 8
                        try:
                            banda8Path = self.dlg.lineEdit_3.text()
                            # verifica banda 8
                            if banda8Path is None or banda8Path == "":
                                self.pop_up(2, "Erro: Nenhum arquivo JP2 selecionado no Banda B", 2)
                            else:
                                try:
                                    # cria nomes para os arquivos carregados
                                    shapeNome = "Shape"
                                    banda4Nome = "Banda 4"
                                    banda8Nome = "Banda 8"
                                    # adiciona os arquivos no layer
                                    self.iface.addRasterLayer(banda4Path, banda4Nome)
                                    self.iface.addRasterLayer(banda8Path, banda8Nome)
                                    self.iface.addVectorLayer(shapePath, shapeNome, "ogr")
                                    # recortar a banda 
                                    self.recortar_raster(shapeNome, banda8Nome)
                                    self.recortar_raster(shapeNome, banda4Nome)
                                    # pegando o cálculo selecionado
                                    funcao = self.dlg.comboBox.currentText()
                                    # calculando NDVI
                                    self.calcular_ndvi("Recorte da Banda 4", "Recorte da Banda 8", funcao)

                                    try:
                                        ndvi = QgsProject.instance().mapLayersByName("NDVI")[0]
                                        self.aplicar_espectro(ndvi)
                                    except: 
                                        self.pop_up(2, "Erro: ao carregar arquivos arquivo de NDVI", 2)

                                except Exception as exc:
                                    self.pop_up(2, "Erro: ao carregar arquivos no Layer", 2)
                                    print(exc)
                        except:
                            self.pop_up(2, "Erro: ao carregar o path de Banda 8", 2)
                except:
                    self.pop_up(2, "Erro: ao carregar o path de Banda 4", 2)
        except:
            self.pop_up(2, "Erro: ao carregar o path do arquivo", 2)
    
    def recortar_raster(self, shapeNome, rasterNome):
        """
        Esta função recebe o nome do shapefile e do raster a ser cortado
        - Tenta pegar o arquivos do layer
        - criar os parâmetros 
        - Recorta o arquivo com o gdal:cliprasterbymasklayer
        - Adiciona o recorte no layer
        """
        try:
            raster = QgsProject.instance().mapLayersByName(rasterNome)[0]
            try:
                vector = QgsProject.instance().mapLayersByName(shapeNome)[0]
                try:
                    # cria parametros
                    parametros = {
                        "INPUT" : raster,
                        "MASK"  : vector,
                        "OUTPUT": "TEMPORARY_OUTPUT",
                    }
                    # processando mapa
                    mapa = processing.run("gdal:cliprasterbymasklayer", parametros)
                    # pegando o recortando
                    recorte = mapa["OUTPUT"]
                    # atribuindo mapa ao layer
                    self.iface.addRasterLayer(recorte, "Recorte da " + rasterNome)
                except: 
                    self.pop_up(2, f"Erro: ao recortar a banda: {rasterNome}")
            except:
                self.pop_up(2, "Erro: ao pegar vetorial do layer", 2)
        except:
            self.pop_up(2, "Erro: ao pegar rater do layer", 2)

    def calcular_ndvi(self, recorte4Nome, recorte8Nome, funcao):
        """
        # Essa função é responsavel pelo calculo de NDVI
        - Tenta pegar os recortes das bandas
        - Cria os parametros de calculo
        - Faz o calculo com a função passada
        - Adiciona o resultado no Layer.
        """
        try:
            recorteBanda8 = QgsProject.instance().mapLayersByName(recorte8Nome)[0]

            try:
                recorteBanda4 = QgsProject.instance().mapLayersByName(recorte4Nome)[0]

                try:

                    parametros = {
                        "INPUT_A"   :   recorteBanda4,
                        "BAND_A"    :   "1",
                        "INPUT_B"   :   recorteBanda8,
                        "BAND_B"    :   "1",
                        "FORMULA"   :   funcao,
                        "OUTPUT"    :   "TEMPORARY_OUTPUT",
                        "RTYPE"     :   5,
                        "NO_DATA"   :   "",
                    }

                    mapa = processing.run("gdal:rastercalculator", parametros)
                    ndvi = mapa["OUTPUT"]

                    self.iface.addRasterLayer(ndvi, "NDVI")
                                     
                except:
                    self.pop_up(2, "Erro: ao processar os recortes", 2)
            except:
                self.pop_up(2, "Erro: ao carregar recorte 4", 2)
        except:
            self.pop_up(2, "Erro: ao carregar recorte 8", 2)

    def aplicar_espectro(self, ndvi):
        try:
            ndviDados = ndvi.dataProvider().bandStatistics(1, QgsRasterBandStats.All, ndvi.extent(), 0)
            maximo = ndviDados.maximumValue
            minimo = ndviDados.minimumValue
            
            # Definindo classes
            classe0 = minimo
            classe2 = minimo + self.encontra_meio(minimo, maximo)
            classe1 = minimo + self.encontra_meio(minimo, classe2)
            classe3 = classe2 + self.encontra_meio(classe2, maximo)
            classe4 = maximo
            # vetor de classes
            valores = [classe0, classe1, classe2, classe3, classe4]
            espectro = [
                QgsColorRampShader.ColorRampItem(valores[0], QColor("#d7191c")),
                QgsColorRampShader.ColorRampItem(valores[1], QColor("#fdae61")),
                QgsColorRampShader.ColorRampItem(valores[2], QColor("#ffffc0")),
                QgsColorRampShader.ColorRampItem(valores[3], QColor("#a6d96a")),
                QgsColorRampShader.ColorRampItem(valores[4], QColor("#33a02c"))
            ]

            # criando um Shader e uma rampa de coloração
            shader = QgsRasterShader()
            rampaCor = QgsColorRampShader()

            rampaCor.setColorRampType(QgsColorRampShader.Interpolated)
            rampaCor.setColorRampItemList(espectro)
            # atribuindo a rampa ao shader
            shader.setRasterShaderFunction(rampaCor)
            # criando o renderizador
            render = QgsSingleBandPseudoColorRenderer(ndvi.dataProvider(), 1, shader)
            # atribuindo os máximos e minimos
            render.setClassificationMin(minimo)
            render.setClassificationMax(maximo)
            # renderizando e colorindo
            ndvi.setRenderer(render)
            ndvi.triggerRepaint()

            # Salvando o raster NDVI
            ndviSalvar = QgsProject.instance().mapLayersByName("NDVI")[0]
            pathNDVI = QFileDialog.getSaveFileName(self.dlg, "Select output file", "", "*.tif")
            # criando um pipe para salvar os dados do NDVI criado
            pipe = QgsRasterPipe()
            pipe.set(ndviSalvar.renderer().clone())
            pipe.set(ndviSalvar.dataProvider().clone())
            # passado o caminho onde escrever os dados
            arquivoRaster = QgsRasterFileWriter(pathNDVI[0])
            # escrevendo
            arquivoRaster.writeRaster(pipe, ndviSalvar.width(), ndviSalvar.height(), ndviSalvar.extent(), ndviSalvar.crs())
            
        except Exception as e:
            print(f"Erro:{e}")
    
    def encontra_meio(self, menorValor, maiorValor):
        return ((maiorValor - menorValor) / 2.0)
    
    def gerar_estatistica(self):
        try:
            # obtendo o shape e o ndvi porduzidos
            shape = QgsProject.instance().mapLayersByName("Shape")[0]
            ndvi = QgsProject.instance().mapLayersByName("NDVI")[0]
            # estabelecendo parametros 
            parametro = {
                "COLUMN_PREFIX": "NDVI",
                "INPUT": shape,
                "INPUT_RASTER": ndvi,
                "OUTPUT": "TEMPORARY_OUTPUT",
                "RASTER_BAND": 1,
                "STATISTICS":[0, 1, 2, 3, 4, 5, 6, 7, 10, 11],
            }
            # processando e obtendo o receorte do mapa raster
            dados = processing.run("native:zonalstatisticsfb", parametro)
            shape = dados['OUTPUT']
            # salvando em um CSV
            filename, _  = QFileDialog.getSaveFileName(self.dlg, "Select output file", "*csv")
            QgsVectorFileWriter.writeAsVectorFormat(
                shape,
                filename,
                "utf-8",
                shape.crs(),
                "CSV",
                attributes=[0, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]
            )
        except Exception as e:
            self.pop_up(2, f"Erro:ceres:gerarEstatíticas:{e}", 2)
    
    """
        # FUNÇÕES PARA FUNÇÕES
    """
    # lendo o arquivo de funções
    def carregar_funcoes(self):
        try:
            with open(self.plugin_dir + '/func.json', 'r') as arquivoFuncao:
                dados = json.load(arquivoFuncao)
            
            listaFuncoes = dados["functions"]

            return listaFuncoes
        
        except Exception as erro:
            self.pop_up(2, "Erro: ao carregar arquivo de funçoes", 2)
            return None

    def valida_expressao(self, expressao):
        try:
            arvoreSintatica = ast.parse(expressao, mode="eval")
            for no in ast.walk(arvoreSintatica):
                if isinstance(no, ast.Name) and not isinstance(no.ctx, ast.Load):
                    raise NameError(f"Simbolo não definido: {no.id}")
            return True
        except SyntaxError as err:
            print(f"Erro de Sintaxe: Simbolo não definido:{err}")
            return False
        except NameError as err:
            print(f"Erro de Definição de Nome:{err}")
            return False
        
    def adicionar_funcao(self):
        funcaoUsuario = self.dlg.lineEdit_4.text().strip()

        if self.valida_expressao(funcaoUsuario):
            try:
                with open(self.plugin_dir + '/func.json', 'r') as arquivoFuncao:
                    dados = json.load(arquivoFuncao)
                dados["functions"].append(funcaoUsuario)

                with open(self.plugin_dir + '/func.json', 'w') as arquivoFuncao:
                    json.dump(dados, arquivoFuncao, indent=2)
                
                # Recarregando a lista de funções
                self.listaFuncoes = self.carregar_funcoes()
                # Limpando o comboBox
                self.dlg.comboBox.clear()
                self.dlg.comboBox_2.clear()
                # Self adiciona a lista
                self.dlg.comboBox.addItems(self.listaFuncoes)
                self.dlg.comboBox_2.addItems(self.listaFuncoes)
                # limpando a linha de edição
                self.dlg.lineEdit_4.clear()
                
            except Exception as err:
                self.pop_up(2, "Erro: falha ao salvar funçao", 2)
        else:
            self.pop_up(2, "Erro: ao ao cadastrar função (expressão invalida)", 2)

    def remover_funcao(self):
        try:
            with open(self.plugin_dir + '/func.json', 'r') as json_file:
                dados = json.load(json_file)
            
            try:
                funcaoSelecionada = self.dlg.comboBox_2.currentText()
                dados["functions"].remove(funcaoSelecionada)

                try:
                    with open(self.plugin_dir + '/func.json', 'w') as json_file:
                        json.dump(dados, json_file, indent=2)
                    
                    self.listaFuncoes = self.carregar_funcoes()
                    self.dlg.comboBox.clear()
                    self.dlg.comboBox_2.clear()
                    self.dlg.comboBox.addItems(self.listaFuncoes)
                    self.dlg.comboBox_2.addItems(self.listaFuncoes)
                    
                except Exception as err:
                    self.pop_up(2, "Erro ao salvar funções", 2)
            except Exception as err:
                self.pop_up(2, "Erro ao remover a função", 2)
        except Exception as err:
            self.pop_up(2, "Erro: ao ler arquivo de funções", 2)

    """
        # METODO PRINCIPAL
    """
    def run(self):
        """Run method that performs all the real work"""
        self.listaFuncoes = self.carregar_funcoes()
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = CeresDialog()
            self.dlg.label_8.setText("Click no botão para fazer download")
            # adicioanando a lista  de funções no combobox
            self.dlg.comboBox.addItems(self.listaFuncoes)
            self.dlg.comboBox_2.addItems(self.listaFuncoes)


        self.dlg.label_8.setText("Click no botão para fazer download")
        # show the dialog
        self.dlg.show()

        """
        +---------------------------+
        | limpa as linhas de edição |
        +---------------------------+ 
        """
        #Linha do shapefile
        self.dlg.lineEdit.clear()
        #Linha de shapefile 4
        self.dlg.lineEdit_2.clear()
        #Linha de shapefile 8
        self.dlg.lineEdit_3.clear()
                
        """
        +---------------------------+
        |   conectores de botões    |
        +---------------------------+
        """
        self.dlg.pushButton.clicked.connect(self.login)
        self.dlg.commandLinkButton.clicked.connect(self.abir_site_copernicus)
        self.dlg.pushButton_2.clicked.connect(self.download)
        self.dlg.toolButton.clicked.connect(self.carregar_shape_file)
        self.dlg.toolButton_2.clicked.connect(self.carrega_banda_4)
        self.dlg.toolButton_3.clicked.connect(self.carrega_banda_8)
        self.dlg.pushButton_3.clicked.connect(self.gerar_mapa_ndvi)
        self.dlg.pushButton_4.clicked.connect(self.adicionar_funcao)
        self.dlg.pushButton_5.clicked.connect(self.remover_funcao)
        
        # desliga a segunda aba
        self.dlg.tabWidget.setTabEnabled(1, False)

        # verifica se  o botão de lembre esta ativo
        if not self.dlg.checkBox.isChecked():
            # limpa os campos de login e de senha
            self.dlg.lineEdit_5.clear()
            self.dlg.mLineEdit.clear()
        
        # Run the dialog event loop
        result = self.dlg.exec_()
        
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
       
        
        """
        +------------------------------+
        |   desconectores de botões    |
        +------------------------------+
        """
        self.dlg.pushButton.clicked.disconnect(self.login)
        self.dlg.pushButton_2.clicked.disconnect(self.download)
        self.dlg.toolButton.clicked.disconnect(self.carregar_shape_file)
        self.dlg.toolButton_2.clicked.disconnect(self.carrega_banda_4)
        self.dlg.toolButton_3.clicked.disconnect(self.carrega_banda_8)
        self.dlg.pushButton_3.clicked.disconnect(self.gerar_mapa_ndvi)
        self.dlg.pushButton_4.clicked.disconnect(self.adicionar_funcao)
        self.dlg.pushButton_5.clicked.disconnect(self.remover_funcao)
