import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('dades_graus_upc.csv', header = 0, engine = 'python',
                 dtype = 'str', keep_default_na = False)

# Percentatge total d'optativitat
total_optatives = df.loc[df.loc[:,'Tipus assig.'] == 'Optativa',:].shape[0]
total_assignatures = df.loc[df.loc[:,'Tipus assig.'] != '',:].shape[0]

print("Percentatge total d'oferta d'assignatures optatives : {:3.2} %".format(total_optatives/total_assignatures*100))

# Percentatge total d'optativitat incloent-hi mencions
total_optatives_i_mencions = df.loc[(df.loc[:,'Tipus assig.'] == 'Optativa') | \
                                    (df.loc[:,'Menció assig'] !=''),:].shape[0]

print("Percentatge total d'ofertad'assignatures optatives i de menció : {:3.2} %".format(
    total_optatives_i_mencions/total_assignatures*100))


# Distribució de crèdits de les assignatures obligatòries, optatives i treballs finals de grau

# Llista per a desar les figures i eixos, per tal que no es perdin
figures = []

tipus_assignatura = ['Obligatòria', 'Optativa', 'Projecte']

for t in tipus_assignatura:
    aux = df.loc[df.loc[:,'Tipus assig.']==t ,'Crèdits assig'].value_counts()

    # Ordenen els valors de value_counts() passant l'índex de la sèrie resultant a tipus float
    aux.index = [float(x) for x in aux.index]
    aux = aux.sort_index()
    aux.index = [str(x) for x in aux.index]
    
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1, projection = 'rectilinear')
    ax.bar(aux.index, aux)
    ax.set_xlabel('Crèdits ECTS')
    ax.set_ylabel("Nombre d'assignatures")
    ax.set_title("Tipus d'assignatures : " + t)

    figures.append({'figura': fig, 'eixos': ax})

plt.show()
