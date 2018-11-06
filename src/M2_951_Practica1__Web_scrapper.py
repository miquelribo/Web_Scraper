import requests as rq
import urllib.robotparser as rp
import bs4
import re
import time as tm
import csv
import sys



class Temporitzador:
    """
    Temporitzador per a espaiar descàrregues de llocs web.
    """
    def __init__(self, temps_espera, tipus = 'relatiu'):
        """
        Retorna un objecte de classe Temporitzador amb els atributs següents:
            darrer_fi_espera : temps d'época (mòdul time) en segons en què va acabar la darrera
                               espera
            tipus : tipus per defecte de temporitzador (pot ser canviat puntualment a cada crida
                    del mètode espera(). Si és 'relatiu' (valor per defecte), espera la quantitat
                    de temps necessari per tal que,entre la fi de la darrera espera ik la fi de
                    la nova espera hagin transcorregut temps_espera segons. Si en cridar el mètode
                    espera() ja s'ha superat aquest intèrval de temps, el temporitzador no espera
                    més. Si es 'absolut' (o qualsevol altre valor diferent de relatiu) el temps
                    serà temps_espera a partir del moment de la crida al mètode espera().
            temps_espera : valor per defecte del temps d'espera (pot ser canviat puntualment a cada
                           crida del mètode espera()). Valors negatius desactiven el temporitzador.
        """
        self.temps_espera = temps_espera
        self.tipus = tipus
        self.darrer_fi_espera = None

    def espera(self, temps_espera = None, tipus = None):
        """
        Espera el temps en segons especificat per defecte al constructor de la classe o el temps
        especificat en temps_espera, segons el tipus de funcionament especificat per defecte al
        constructor de la classe o el mètode especificat a tipus. 
        """
        # Si hi ha valors puntuals per a temps_espera o tipus, els emprem en comptes
        #d els valors per defecte. Sinó, emprem els valors per defecte 
        if temps_espera == None:
            temps_espera = self.temps_espera
        if tipus == None:
            tipus = self.tipus
            
        if temps_espera<=0:
            # No cal esperar...
            segons_espera = 0
        elif tipus== 'relatiu':
            # Espera relativa a la fi de la darrera espera, si n'hi ha
            if self.darrer_fi_espera:
                # Si ja hem esperat alguna vegada, cal esperar, com a molt, self.temps_espera
                segons_espera =  temps_espera - (tm.time() - self.darrer_fi_espera)
                # Si quan cridem el mètode ja han passat més de temps_espera segons des de la
                # darrera crida, segons_espera serà negatiu, i no caldrà esperar un temps addicional
            else:
                # Si encara no hem esperat mai, no cal esperar ara
                segons_espera = 0
        else:
            # Espera absoluta en cridar el mètode
            segons_espera = temps_espera

        if segons_espera > 0:
            tm.sleep(segons_espera)

        # Desem el moment de fi d'espera per a ús o referència futures
        self.darrer_fi_espera = tm.time()



def descarrega_url(url, intents = 5, timeout = 10, agent_usuari = 'ua0000', retorna = 'text'):
    """
    Funció que obté els continguts del lloc web indicat per url, si aquest no està desabilitat al fitxer robots.txt

    Arguments:
        url          : url del lloc web del qual obtenir-ne els continguts
        intents      : nombre d'intents si s'obté un codi de resposta diferent de 200 (per defecte 5 vegades)
        timeout      : temps màxim durant el qual s'espera resposta del servidor (per defecte 1s)
        agent_usuari : agent usuari per a la petició GET (per defecte 'ua00')
        retorna      : format de les dades a retornar, text o binari. Valor per defecte, 'text'. Qualsevol
                       altre valor fa que es retornin en format binari
    Retorna:
        contingut      : dades obtingudes com a resposta del lloc url a la petició GET. No tenen perquè ser codi html,
                         poden ser una imatge, un arxiu pdf o qualsevol altre conjunt de dades binàries o text.
        codi_error     :
                         * 0 si no hi ha hagut cap error
                         * -1 si el lloc web està prohibit per robots.txt
                         * -2 si s'ha superat el timeout especificat
                         * -3 si hi ha hagut algun altre error de transmissió
                         * el nombre d'error del protocol HTTP si s'ha produït aquest error (si l'error és del
                           servidor (codis 500 a 599) la funció genera automàticament intents reintents per a mirar
                           d'obtenir una transmissió correcta)
        missatge_error : missatge d'error explicatiu de l'error obtingut
    
    Nota: Només es generen reintents quan hi ha un error de servidor. Quan hi ha errors de transmissió o de
    timeout, cal fer la gestió de reintents externament.
        
    """

    # Comprovem si podem accedir a la pàgina al fitxer robots.txt. Si no podem,
    # generem un error i retornem sense accedir-hi
    robot = rp.RobotFileParser()
    robot.set_url('http://www.uoc.org/robots.txt')
    robot.read()
    if not robot.can_fetch(agent_usuari, url):
        contingut = None
        codi_error = -1
        missatge_error = "Lloc web prohibit per robots.txt"
        return contingut, codi_error, missatge_error
    
    # Fem una petició de la pàgina web especificada pel paràmetre url
    try:
        capcalera = {'User-agent': agent_usuari}
        
        t_inici_peticio = tm.time()
        pagina = rq.get(url, timeout = timeout, headers = capcalera)
        t_fi_peticio = tm.time()
        # Desem el temps de resposta per si cal repetir la petició si hi ha errors de servidor
        t_resposta = t_fi_peticio - t_inici_peticio
        
    except rq.exceptions.Timeout:
        # Si s'ha superat el time-out sense resposta, retornem un error i sortim
        contingut = None
        codi_error = -2
        missatge_error = "S'ha superat el timeout especificat ({} s)".format(timeout)
        return contingut, codi_error, missatge_error

    except:
        # Si hi ha hagut algun altre problema inidentificat, retornem un error i sortim
        contingut = None
        codi_error = -3
        missatge_error = "Hi ha hagut un problema inidentificat amb la connexió"
        return contingut, codi_error, missatge_error

    # Si hi ha hagut un error de servidor (i intents>0), repetim recursivament fins
    # a intents vegades la petició, a veure si l'error desapareix
    if (intents>0) and (500<=pagina.status_code<600):
        # Esperem un temps equivalent a 10 vegades el temps de resposta i tornem a iniciar
        # el procés
        print(intents)
        temporitzador = Temporitzador(10*t_resposta,'absolut') 
        temporitzador.espera()
        
        return descarrega_url(url, intents = intents-1, timeout = timeout)

    # Si hi ha qualsevol error o imprevist detectat pel servidor, retornem un error i sortim
    if pagina.status_code!=200:
        contingut = None
        codi_error = pagina.status_code
        missatge_error = "S'ha produït l'error HTTP {}".format(pagina.status_code)
        return contingut, codi_error, missatge_error

    # Finalment, si no hi ha hagut errors, retornem un codi d'error 0 i el contingut.
    # Si retorna val 'text', es retorna el contingut en format text. Sinó (si val 'binari',
    # per exemple), es retorna el contingut binari
    contingut = pagina.text if retorna == 'text' else pagina.content
    codi_error = 0
    missatge_error = None
    return contingut, codi_error, missatge_error



def descarrega_pdf(url, nom_directori = ".\\", nom_arxiu = None, intents = 5, timeout = 10, agent_usuari = 'ua0000'):
    """
    Funció que descarrega un document en format pdf de l'adreça directa indicada
    i el desa al directori i amb el nom de fitxer indicats. Empra descarrega_url().
    Arguments:
        url : url de l'arxiu en format pdf (o qualsevol altre format binari) 
              a descarregar
        nom_directori : nom del directori (existent) on desar l'arxiu. Per defecte,
                        ".\"
        nom_arxiu : nom de l'arxiu on es desarà el document. Si no s'indica, es
                    deduix de la url
        intents, timeout, agent_usuari : paràmetre que es passen a descarrega_url()
     Retorna:
         codi_error, missatge_error : fornits per descarrega_url()
    """

    # Aprofitem la funció descarrega pàgina per a baixar els continguts del
    # dcoument en format binari
    doc_pdf, codi_error, missatge_error = descarrega_url(url,
                                                         intents = intents,
                                                         timeout = timeout,
                                                         agent_usuari = agent_usuari, 
                                                         retorna = 'binari')
   
    # Si hi ha hagut algun problema amb la descàrrega del document, retornem
    # el codi d'error adient i p
    if codi_error:
        return codi_error, missatge_error

    # Si no donem un nom, l'inferim de l'adreça url
    if not nom_arxiu:
        nom_arxiu = re.sub(r"\A.+/",'', url)
        
    # Desem el document pdf
    with open(nom_directori + nom_arxiu, 'wb') as f:
        f.write(doc_pdf)
        
    return codi_error, missatge_error

        

def crawlscrape_url_principal():
    """
    Funció que retorna una llista amb les adreces de les pàgines web de cadascun dels graus
    que oferta la UPC, per al seu crawling/scraping posterior.
    
    Retorna:
        graus          : llista amb les url de les pàgines web de cadascun dels graus que oferta la UPC.
                         Si hi ha hagut algun error, retorna una llista buida
        codi_error     : codi d'error de la funció descarrega_url()
        missatge_error : missatge d'error de la funció descarrega_url()
    """
    
    html, codi_error, missatge_error = descarrega_url('https://www.upc.edu/ca/graus/',
                                                      timeout = 10, retorna = 'binari')

    if codi_error:
        # Si hi ha hagut algun error, retornem una llista buida
        graus = []
        return graus, codi_error, missatge_error
    
    # Creem un objecte de BeautifulSoup emprant el parser HTML, "lxml" de la llibreria lxml, instalada.
    # Com a alternativa es pot emprar el parser "html.parser" de la llibreria estàndard de Python,
    # més lent
    bs_UPC = bs4.BeautifulSoup(html,'lxml')

    # Obeneim els tags dels grups de graus
    tags_grups = bs_UPC.body.find_all('div', id = re.compile('collapse-images-collapse'))

    # Obtenim els graus a dins de cada grup
    graus_aux = [x.find_all('li') for x in tags_grups]

    # Aplanem la llista
    tags_graus = [x for subllista in graus_aux for x in subllista]

    # Obtenim la llista d'adreces web dels graus i les desem a una llista de diccionaris
    graus = [i.a['href'] for i in tags_graus]
    
    return graus, codi_error, missatge_error



def crawlscrape_url_grau(url_grau, verbose = True, desa_pdfs = False, nom_directori = ".\\"):
    """
    Funció que obté, a partir de l'URL de la pàgina web d'un grau oficial  
    de la UPC,la informació rellevant sobre el mateix.
    
    Paràmetres:
        url_grau : adreça de la pàgina web del grau
        verbose : si val True (valor per defecte) imprimeix informació sobre el
                  grau que està tractant i problemes trobats
        desa_pdfs : si val True, es desen els documents pdf disponibles associats
                    a les assignatures del grau al directori (existent) especificat. 
                    Valor per defecte: False.
        nom_directori : directori on es desaran els documents pdf de les assignatures. 
                        Valor per defecte: ".\".

    Retorna:
        grau: diccionari amb la informació recopilada amb el format següent:
                { 'Nom' :             nom del grau
                  'URL' :      adreça de la pàgina web del grau
                  'Càrrega lectiva' : nombre de crèdits ECTS del grau
                  'Assignatures' : [ { 'Nom' :             nom de l'assignatura,
                                       'Semestre' :        semestre en què s'imparteix,
                                       'Càrrega lectiva' : càrrega lectiva en crèdits ECTS
                                       'URL' :      adreça de la pàgina web de l'assignatura,
                                       'Tipus':            Obligatòria, Optativa o Projecte
                                       'Menció':           Menció o especialitat de l'assignatura
                                     },
                                     ...
                                   ]
                }
        codi_error : 0 si tot és correcte. Sinó, el codi d'error heretat de
                     descarrega_url() o -4 si no ha pogut obtenir ni el
                     nom del grau
        missatge_error : missatge d'error associat a codi_error

    Nota: Per a les dades que manquen retorna el valor ''.
    """

    # Desarem la informació del grau a un diccionari
    grau = {}
    
    #Descarreguem el contingut del lloc web
    html_aux, codi_error, missatge_error = descarrega_url(url_grau, timeout = 10,
                                                          retorna = 'binari')
    
    # Si hi ha hagut algun problema, n'informem i retornem un diccionari buit amb el
    # codi i missatge d'error
    if codi_error:
        if verbose:
            print("No s'ha pogut descarregar la informació del lloc web "+url_grau)
        return grau, codi_error, missatge_error
    
    # Comencem el procés d'scraping
    bs_aux = bs4.BeautifulSoup(html_aux, 'lxml')
    bs_aux = bs_aux.body.find('div', id = 'main-container')
    
    ###########################
    # Obtenim el nom del grau #
    ###########################
    try:
        tag_nom = bs_aux.header.find('h1', id = 'degree-name')
        # Per a emprar una cadena fora de bs4, millor assignar-la mitjançant unicode() o str()
        # a una altra cadena. Sinó, conserva el tipus original i una referencia a l'objecte bs4
        # del qual prové, que no es destruieix fins que no ho fa la cadena: es malgasta memòria
        nom = str(tag_nom.string).strip()
        grau['Nom'] = nom
        if verbose:
            print(nom.upper())
        grau['URL'] = url_grau
    except:
        # Si hi ha algun problema abandonem la funció sense retornar res
        if verbose:
            print("No s'ha pogut resoldre el nom del grau a " + url_grau)
        grau = {}
        codi_error = -4
        missatge_error
        return grau, codi_error, missatge_error

    ####################################################################################
    # Obtenim els crèdits del màster (hi ha màsters que no tenen informació acadèmica) #
    ####################################################################################
    try:
        tag_inf_academ = bs_aux.find('div', id = 'collapse-images-collapse-academic-information').dl
        # Noms de la informació
        tags_dt = tag_inf_academ.find_all('dt')
        noms_dt = [str(x.string).strip() for x in tags_dt]
        # valors de la informació
        tags_dd = tag_inf_academ.find_all('dd')
        noms_dd = [str(x.string).strip() for x in tags_dd]
        #Obtenim l'índex de la càrrega lectiva, si hi és, i el seu valor
        index = noms_dt.index('Càrrega lectiva')
        grau['Càrrega lectiva'] = noms_dd[index][0:3]
    except:
        # Si hi ha hagut algun problema, desem un valor de '', però continuem
        grau['Càrrega lectiva'] = ''
        if verbose:
            print("  No s'ha pogut obtenir la càrrega lectiva ")
    
    #############################################
    # Si n'hi ha, obtenim les mencions del grau #
    #############################################
    tags_mencions = bs_aux.find('div', class_ = 'pla-estudis-selector')
    if tags_mencions:
        # Si existeix el tag anterior, n'extraiem les mencions
        tags_mencions = tags_mencions.ul.find_all('li')
        mencions = {x['target']: x.string for x in tags_mencions}
        # Simplifiquem el nom de les mencions amb expressions regulars
        mencions = {k : re.sub(r'^Menció en *', '', re.sub(r'kkk$', '', mencions[k]))
                    for k in mencions.keys()}
    else:
        mencions = {}
    
    ##################################################################################
    # Obtenim el les assignatures, el semestre d'oferta i la seva càrrega acadèmica. # 
    # Hi ha graus que no el tenen, i hi ha graus que tenen formats lleugeramanet     #
    # diferents per a les dades de les assignatures.                                 #
    ##################################################################################
    grau['Assignatures'] = []
    try:
        # Obtenim la llista de tags de semestres
        tags_semestres = bs_aux.find('div', id = 'collapse-images-collapse-curriculum')
        tags_semestres = tags_semestres.find_all('div', attrs = {'class': 'pla-estudis-quadrimestre',
                                                                 'id': False})
        # Si obtenim una llista buida de semestres, informem que no s'ha pogut obtenir el pla
        # d'estudis i retornem
        if not tags_semestres:
            if verbose:
                print("  No s'ha pogut obtenir el pla d'estudis")
            # Tot i que no s'han pogut obtenir les assignatures, es retorna el codi
            # d'error de descarrega_url que, si s'ha arribat ací, és 0 (sense error)
            return grau, codi_error, missatge_error
    except:
        # Si hi ha hagut algun altre problema, també sortim
        if verbose:
            print("  No s'ha pogut obtenir el pla d'estudis")
        return grau, codi_error, missatge_error
    
    # Extraiem les dades d'assignatures de cada semestre, i les desem a la llista
    for s in range(len(tags_semestres)):
        semestre = s+1
        try:
            tags_assignatures = tags_semestres[s].ul.find_all('li')

            for assignatura in tags_assignatures:
                if len(assignatura['class'])==2:
                    # En graus sense mencions class té dos atributs, "sense-especialitat" i
                    # "Obligatòria"/"Optativa"/"Projecte"
                    mencio = ''
                else:
                    # En graus sense mencions class té tres atributs, "especialitat", "especialitat-i" i
                    # "Obligatòria"/"Optativa"/"Projecte"
                    mencio = mencions[assignatura['class'][1]]
                tipus = assignatura['class'][-1] # Obligatòria, Optativa o Projecte                
                carrega_lectiva = str(assignatura.span.string)
                 # Si l'assignatura té el tag a, que conté el nom i adreça web de l'assignatura
                if assignatura.a:
                    adreca_web = assignatura.a['href']
                    nom = str(assignatura.a.string).strip()
                else:
                    # Sinó, el nom és directament al contingut del tag li, amb altres elements.
                    # Recuperem tots els continguts del tag, eliminant els continguts que són espais
                    # blans, en una llista. El primer element serà el nom de l'assignatura
                    adreca_web = ''
                    nom = str([x for x in assignatura.contents if x not in [' ']][0]).strip()
                # Desem les dades a un diccionari per assignatura i l'adjuntem a la llista d'assignatures
                # del pla d'estudis.
                grau['Assignatures'].append({'Nom': nom,
                                             'Semestre': str(semestre),
                                             'Càrrega lectiva': carrega_lectiva,
                                             'URL': adreca_web,
                                             'Tipus': tipus,
                                             'Menció': mencio})
        except:
            if verbose:
                print("  No s'han pogut extreure (algunes de) les assignatures del semestre " + 
                      str(semestre))

    #######################################################################
    # Per a graus amb mencions, eliminem duplicats d'assignatures comunes # 
    # a TOTES les mencions                                                #
    #######################################################################
    if mencions and grau['Assignatures']:
        i = 0
        while i<len(grau['Assignatures']):
            # Busquem les posicions dels duplicats d'una assignatura
            posicions_duplicats = [j for j in range(i+1, len(grau['Assignatures'])) if (
                                   grau['Assignatures'][j]['Nom'] == grau['Assignatures'][i]['Nom'] and
                                   grau['Assignatures'][j]['Tipus'] == grau['Assignatures'][i]['Tipus']  and
                                   grau['Assignatures'][j]['URL'] == grau['Assignatures'][i]['URL'])]
            # Si n'hi ha un menys que el nombre de mencions, els esborrem i eliminen la referència a la menció
            if len(posicions_duplicats) == len(mencions)-1:
                grau['Assignatures'][i]['Menció'] = ''
                for j in posicions_duplicats[::-1]:
                    del grau['Assignatures'][j]
                
            i += 1

    ###########################################################################
    # Si cal desem els documents pdf associats a les assignatures disponibles #
    ###########################################################################
    if desa_pdfs and grau['Assignatures']:
        # Establim un temporitzador relatiu a intèrvals de 5 segons i l'executem
        # una 1a vegada per a fixar darrer:fi_espera
        temp2 = Temporitzador(5, 'relatiu')
        temp2.espera()
        for assignatura in grau['Assignatures']:
            temp2.espera()
            # Si l'assignatura té adreça web del seu document pdf associat,
            # el descarreguem
            if assignatura['URL']:
                try: 
                    # Com que aquest és un procés secundari, informem si hi
                    # ha hagut algun problema, però no passem els codis d'error
                    # cap a nivells superiors de codi ni sortim de la funció
                    codi_error_aux, missatge_error_aux = \
                      descarrega_pdf(assignatura['URL'],
                                     nom_directori = nom_directori)
                    if verbose and codi_error_aux:
                        print("  Hi ha hagut algun problema amb l'obtenció del document" +
                                "pdf de la url " + assignatura['URL'])
                except:
                    if verbose:
                        print("  No s'han pogut desar el document pdf de la url " + 
                              assignatura['URL'])
           
    return grau, codi_error, missatge_error



####################################
######## PROGRAMA PRINCIPAL ########
####################################

if __name__ == '__main__':
    # Obtenim les url dels llocs webs dels graus de la UPC
    webs_graus, codi_error, missatge_error = crawlscrape_url_principal()
    
    # Si hi ha hagut algun error, sortim del programa
    if codi_error:
        print("No s'han pogut obtenir les url dels graus")
        print("Error: ", (codi_error, missatge_error))
        sys.exit()
    
    # Creem un temporitzador relatiu (espaiarem les peticions un mínim de 20s)
    temp = Temporitzador(20, 'relatiu')
    # L'executem una vegada per a alinear l'atribut darrer_fi_espera amb el
    # temps actual
    temp.espera()
    
    # Creem el fitxer csv de dades
    with open('dades_graus_upc.csv', 'w', newline='') as f:
        writer = csv.writer(f, delimiter = ',', quoting = csv.QUOTE_ALL)
        # Escrivim la capçalera
        writer.writerow(['Nom grau',
                         'URL grau',
                         'Crèdtis grau',
                         'Nom assig',
                         'URL assig',
                         'Crèdits assig',
                         'Tipus assig',
                         'Semestre assig',
                         'Menció assig'])
        for w in webs_graus:
            temp.espera()
            dades, codi_error, missatge_error = crawlscrape_url_grau(w)
            # Si no s'ha pogut obtenir ni informació bàsica del grau, no es desa res
            if codi_error:
                print("No s'han pogut obtenir les dades de " + w)
                continue
            # Si s'ha pogut obtenir informació d'assignatures, es genera un iterable amb tants
            # elements com assignatures al grau i les dades generals del grau repetides per assignatura
            if dades['Assignatures']:
                iterable = ([dades['Nom'],
                             dades['URL'],
                             dades['Càrrega lectiva'],
                             x['Nom'],
                             x['URL'],
                             x['Càrrega lectiva'],
                             x['Tipus'],
                             x['Semestre'],
                             x['Menció']] for x in dades['Assignatures'])
                writer.writerows(iterable)
            # Sinó, s'escriu una fila amb les dades generals del grau i
            # sense cap dada d'assignatura
            else:
                writer.writerow([dades['Nom'],
                                 dades['URL'],
                                 dades['Càrrega lectiva'],
                                 '',
                                 '',
                                 '',
                                 '',
                                 '',
                                 ''])
