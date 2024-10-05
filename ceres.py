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
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .ceres_dialog import CeresDialog
import os.path

# Minhas importações
from qgis.gui   import QgsMessageBar
from qgis.core  import(
    Qgis,
    QgsApplication
  
)
from PyQt5.QtCore   import QUrl
from PyQt5.QtGui    import QDesktopServices
import json
import requests



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
        # METODOS PARA LOGIN, LEMBRE-ME E CADAATRO NO COPERNICUS
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
        

        #print(self.user+"\n"+self.senha)

        print("Login: "+self.user["user"]["login"])
        print("Pass: "+ self.user["user"]["pass"])

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

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = CeresDialog()

        # show the dialog
        self.dlg.show()
        
        """
        +---------------------------+
        |   conectores de botões    |
        +---------------------------+
        """
        self.dlg.pushButton.clicked.connect(self.login)
        self.dlg.commandLinkButton.clicked.connect(self.abir_site_copernicus)
        
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
        
       