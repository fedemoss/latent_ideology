import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.utils.extmath import randomized_svd

class latent_ideology:
  """
  Method for applying the correspondence analysis method for the purpose of calculating 
  an 'ideology score' as stated in [1][2].

  [1] J. Flamino, A. Galezzi, S. Feldman, M. W. Macy, B. Cross, Z. Zhou, M. Serano, A. Bovet, H. A. Makse, and B. K. Szymanski,
  'Shifting polarization and twitter news influencers between two us presidential elections', 
  arXiv preprint arXiv:2111.02505 (2021).

  [2] Max Falkenberg, Alessandro Galeazzi, Maddalena Torricelli, Niccolo Di Marco, Francesca Larosa, Madalina Sas, Amin Mekacher, 
  Warren Pearce, Fabiana Zollo, Walter Quattrociocchi, Andrea Baronchelli,
  'Growing polarisation around climate change on social media',
  https://doi.org/10.48550/arXiv.2112.12137 (2021).

  """

  def __init__(self, df):
    self.df = df

  #from dataframe, return filtered pandas adjacency matrix 
  def make_adjacency(self, m = None ,n = 2, k=None, targets = 'target', sources= 'source', weight = False, weight_name = 'weight',filtered_df = False, detailed_lists = False, drop = None):
    """
    Create weighted adjacency matrix from unfiltered -optionally- pandas dataframe input.
    The input dataframe consist of interactions between a target and a source
    ## Parameters:
    -  **m** : int (default = None). 
            Number of sources to consider (default = consider all sources in the dataset).
    -  **n** : int (default = 2). 
            Number of distinct sources interacting with each target.
    -  **k** : int (default = None)
            Maximum interactions between each target and all sources (default = consider all existing interactions).
    -  **targets** : str (default = 'target'). 
            Name of the column of the targets
    -  **sources** : str (default = 'source'). 
            Name of the column of the sources
    -  **weight** : bool (default = False) -if False, time of execution takes longer-
            Does your data have a weight column indicating how many times a target had interacted with each source?
            (if True, specify the column name in the next parameter).
    -  **weight_name** : str (default = False)
            if weight==True, specify the name of the column associated with the weight of the interaction target/source.
    -  **filtered_df** : bool (default = 'weight').
            Returns a filtered (given thresholds m,n) dataframe, similar to the input one.
            It also adds a column associated with the weight of the connection beetween a 
            target and a source 
    - **detailed_lists** : bool (default = False) 
            Returns 2 extra dataframes indicating which sources had the targets interacted with, and viceversa.
    - **drop** : list (default = None).
            List of targets/sources to drop before applying the method.
    """
    df = self.df.copy()
    df['target'] = df[targets]
    df['source'] = df[sources]
    if weight==True:
      df['weight'] = df[weight_name]
    if m==None:
      m = len(df.target) 
    if k==None:
      k = 1e23 #enourmous number that resembles the non-filtering case

    #Drop them!
    if drop!=None:
      target_todrop = []
      source_todrop = []
      for obj in drop:
        target_todrop.append(list(df[df.target == obj].index))
        source_todrop.append(list(df[df.source == obj].index))
      x1=sum(target_todrop, [])
      x2=sum(source_todrop, [])
      fulldrop = x1+x2
      df = df.drop(fulldrop, axis=0).reset_index(drop=True).copy()


    #Threshold 0: Interactions limit
    df2 = pd.DataFrame()
    df2['counter'] = df[['target','source']].groupby('target').count().sort_values(by = 'source', ascending = False).source
    interactions_count = df2.query('counter < @k').index
    df_th0 = df[df.target.isin(interactions_count)].copy()  

    #Threshold 1: number of distinct sources interacting with each target
    groups_dict_target = df_th0[['target','source']].groupby(by=['target']).groups #dict
    keys_list = list(groups_dict_target.keys()) #users (keys)
    sources = []
    lengths = []
    total_interactions = []
    
    for key in keys_list:
      source_list_index = list(groups_dict_target[key]) #sources list for each target 
      source_asocciated = []
      for s in source_list_index:
        source_asocciated.append(df.source[s])
      total_interactions.append(len(source_list_index))
      sources.append(list(set(source_asocciated)))
      lengths.append(len(list(set(source_asocciated)))) #list of sources lenghts
    data = {'target':keys_list, 'sources_associated':sources, 'total_distinct_sources':lengths, 'total_interactions':total_interactions}#new df
    df3 = pd.DataFrame(data).sort_values(by=['total_distinct_sources'], ascending=False).reset_index(drop=True)
    df_targets_associated = df3.query("total_distinct_sources >= @n")
    targets_threshold_1 = list(df_targets_associated['target'])
    df_filtered_th1 = df_th0.query('(target == @targets_threshold_1)')
    
    #Threshold 2: number of sources
    top_sources = df_filtered_th1[['target','source']].groupby('source').count().sort_values(by = 'target', ascending = False).head(m).index
    df_filtered_th1_th2 = df_filtered_th1[df_filtered_th1.source.isin(top_sources)].copy()

    #Unique targets, sources
    source_list = list(df_filtered_th1_th2.source.unique())
    target_list = list(df_filtered_th1_th2.target.unique())

    if detailed_lists:
      targets_info = df_targets_associated[df_targets_associated.target.isin(target_list)]

    #Weights
    if weight == False:
      #Lets add the weight of each interaction
      w = []
      df4 = pd.DataFrame()
      for s in source_list:
        df4['weight'] = df_filtered_th1_th2[df_filtered_th1_th2.source==s][['target','source']].groupby(by='target').source.count()
        df4['source'] = s
        w.append(df4)
        df4 = pd.DataFrame()
      dfw = pd.concat(w).fillna(0).sort_values('weight',ascending=False).groupby(by=['target','source']).sum().reset_index()
    else:
      dfw = df_filtered_th1_th2

    #Detailed source list
    if detailed_lists:
      groups_dict = dfw[['source','target']].set_index('target').groupby(by=['source']).groups
      keys_list = list(groups_dict.keys()) #influencers (keys)
      targets_asoc = []
      lengths = []
      for key in keys_list:
        target_list = list(groups_dict[key]) #target list 
        targets_asoc.append(target_list)
        lengths.append(len(target_list))

      data_new = {'source':[str(key) for key in keys_list], 'targets_associated': targets_asoc, 'total_distinct_targets': lengths} #Create dataframe
      sources_info = pd.DataFrame(data_new).sort_values(by=['total_distinct_targets'], ascending=False).reset_index(drop=True)


    #Final matrix
    source_col = []
    for s in source_list:
      df_aux = dfw[dfw.source == s][['target','weight']].set_index('target') #column users & weights
      df_aux.columns = [s] #rename weight --> influencer asociated 
      source_col.append(df_aux) #list of targets associated with source

    final_data = pd.concat(source_col).fillna(0).groupby('target').sum()

    if filtered_df == True and detailed_lists == False:
      return dfw, final_data
    elif filtered_df == False and detailed_lists == False:
      return final_data
    elif filtered_df == True and detailed_lists == True:
      return dfw, targets_info, sources_info, final_data
    elif filtered_df == False and detailed_lists == True:
      return targets_info, sources_info, final_data
    

  #Use the correpondence analysis method to calculate the scores of a given adjacency matrix in the rows projection
  def calculate_scores(self, A, dimension = 1):
    """
    Normalize, standardized and use SVD to reduce the dimension of a given input matrix.
    The output is a 'score' associated with each row of the input matrix. 
    If multiple dimensions are consider, the 'score' output is a list of scores associated 
    with each dimension (each principal component considered)

    OBS: Since the scores are 'row scores', one can simply trnaspose the input matrix to calculate the
    'column scores'. In the case of an adjacency matrix:
      -  row scores == target scores
      -  column scores == sources scores

  
    This method is further discussed in [1] and [2].
    ## Parameters
    -  **A** : numpy matrix.
            Weighted adjacency matrix.
    -  **dimension** : int (default = 1).
            To how many dimensions shall the truncated SVD method reduce the input matrix A. 
            This is equivalent the number of principal components considered
            when truncating the SVD method.
    """

    P = (1/np.sum(A))*A #Nomalized natrix

    #Defining needings for standardizing
    n_col = np.shape(P)[1]
    n_row = np.shape(P)[0]
    r = np.matmul(P, np.ones((n_col,))) #rows
    c = np.matmul(np.ones((n_row,)), P) #columns
    r2 = r**(-0.5)
    c2 = c**(-0.5)
    Dr2 = np.diag(r2)
    Dc2 = np.diag(c2)
    r_t = np.array([r]).transpose()
    c_new = np.array([c])

    #Standardized residuals
    S = np.matmul(np.matmul(Dr2, P - np.matmul(r_t,c_new)),Dc2)

    if dimension > 1:
      #Truncated SVD
      U, sig, Vt = randomized_svd(S, n_components=dimension, n_iter=5, random_state=None)
      X_dim1 = np.matmul(Dr2,U) #scores matrix
      scores = []
      for i in range(dimension):
        #scaling betweeen -1 and 1 each dimension
        scores.append((-1 + 2 * (X_dim1[:,i]-np.min(X_dim1[:,i]))/np.ptp(X_dim1[:,i]))) #scaled
    else:
      #Truncated SVD
      U, sig, Vt = randomized_svd(S, n_components=1, n_iter=5, random_state=None)
      
      #scores
      X_dim1 = np.matmul(Dr2,U) #scores matrix
      scores = (-1 + 2 * (X_dim1-np.min(X_dim1))/np.ptp(X_dim1)) #scaled
    
    return scores


  #Compute the scores for rows and columns using the built-it correspondence analysis method. 
  #Here, sources scores are calculated transposing the adjacency matrix
  def apply_simplified_method(self, df_adjacency):
    """
    Apply the correspondence analysis method to calculate the row scores given an adjacency matrix.
    The column scores (or the score of the sources) are calculated by transposing the adjacency matrix
    and imposing the exact same treatment as with the original non-transposed adjacency matrix. 

    ## Parameters
   -   **df_adjacency** : pandas dataframe. 
                  Weighted adjacency matrix in the shape of a pandas dataframe.
                  This could be the output from the make_adjacency() funciton.

    """

    A = df_adjacency.to_numpy(dtype = int) #for row scores
    B = df_adjacency.T.to_numpy(dtype = int) #for column scores
    row_scores = self.calculate_scores(A)
    col_scores = self.calculate_scores(B)

    #DataFrame of targets (rows) scores
    scores_list = [float(l) for l in row_scores]
    data_metodo = {'target':df_adjacency.index,'score':scores_list}
    df_scores_target = pd.DataFrame(data_metodo)

    #DataFrame of sources (columns) scores
    scores_list = [float(l) for l in col_scores]
    data_metodo = {'source':df_adjacency.columns,'score':scores_list}
    df_scores_sources = pd.DataFrame(data_metodo)

    return df_scores_target, df_scores_sources

#Compute the scores for rows and columns using the built-it correspondence analysis method as stated in the bibliography
  def apply_method(self, m = None, n = 2, k = None, targets = 'target', sources= 'source', weight = False, weight_name = 'weight', detailed_lists = False, drop = None, weighted_mean=False):
    """
    Apply the correspondence analysis method to calculate the row scores given a source-target interaction dataframe.
    The column scores (or the score of the sources) correspond to the mean othe target scores
    associated with a given source. Just like [1][2].

    This function transform a dataframe of interactions into an adjacency matrix. This proccess takes
    into consideration some filtering. 
    This can be further studied by looking into the built-in function 'make_adjacency()'

    ## Parameters
    -  **m** : int (default = None). 
            Number of sources to consider (default = consider all sources in the dataset)
    -  **n** : int (default = 2). 
            Number of distinct sources interacting with each target
    -  **k** : int (default = None)
            Maximum interactions between each target and all sources (default = consider all existing interactions). 
    -  **targets** : str (default = 'target'). 
            Name of the column of the targets
    -  **sources** : str (default = 'source'). 
            Name of the column of the sources
    -  **weight** : bool (default = False) -if False, time of execution takes longer-
            Does your data have a weight column indicating how many times a target had interacted with each source?
            (if True, specify the column name in the next parameter).
    -  **weight_name** : str (default = False)
            If weight==True, specify the name of the column associated with the weight of the interaction target/source.
    -  **detailed_lists** : bool (deafault = False)
            If True, returns 2 extra dataframes indicating which sources had the targets interacted with, and viceversa.
    - **drop** : list (default = None).
            List of targets/sources to drop before applying the method.
    - **weighted_mean** : Bool (default = False)
            Calculate the score of the sources by a weighted mean of the scores of the targets. If False, the scores are calculated by the
            non-weighted mean, as the bibliography indicates.       

    """

    #Adjacency matrix & filtering
    if detailed_lists:
      df_filtered, targets_info, sources_info ,df_adjacency = self.make_adjacency(m=m,n=n,k=k,targets=targets, sources=sources, filtered_df=True, weight=weight, weight_name=weight_name, detailed_lists=detailed_lists, drop=drop)
    else:
      df_filtered, df_adjacency = self.make_adjacency(m=m,n=n,k=k,targets=targets, sources=sources, filtered_df=True, weight=weight, weight_name=weight_name, detailed_lists=detailed_lists, drop=drop)

    #DataFrame of targets (rows) scores
    A = df_adjacency.to_numpy(dtype = int) #for row scores
    row_scores = self.calculate_scores(A)
    scores_list = [float(l) for l in row_scores]
    data_metodo = {'target':df_adjacency.index,'score':scores_list}
    df_scores_target = pd.DataFrame(data_metodo)

    #DataFrame of sources (columns) scores
    df_final = df_filtered.set_index('target').join(df_scores_target.set_index('target'))
    df_final['target'] = df_final.index
    df_final = df_final.reset_index(drop=True).copy()

    if weighted_mean:
      groups_dict = df_final[['source','score','weight']].set_index('score').groupby(by=['source', 'weight']).groups

      keys_list_sources = list(df_final[['source','score','weight']].set_index('score').groupby(by=['source']).groups.keys()) #sources
      keys_list = list(groups_dict.keys()) #tuples

      mean_scores_w = []
      score_list_w = []
      length_w = []
      last_key = keys_list[0][0]
      for key in keys_list:
        if key[0] == last_key:
          score_list_w.append(np.sum(list(groups_dict[key])) * key[1])
          length_w.append(len(list(groups_dict[key])) * key[1])

          last_key = key[0]
        else:
          mean_scores_w.append(np.sum(score_list_w)/np.sum(length_w))

          score_list_w = []
          length_w = []
          score_list_w.append(np.sum(list(groups_dict[key])) * key[1])
          length_w.append(len(list(groups_dict[key])) * key[1])
          last_key = key[0]

        if key == keys_list[-1]: #last key
          mean_scores_w.append(np.sum(score_list_w)/np.sum(length_w))


      data_new = {'source':[str(key) for key in keys_list_sources], 'score':mean_scores_w} #Create dataframe
      df_scores_source = pd.DataFrame(data_new).sort_values(by=['score'], ascending=False).reset_index(drop=True)
          
    else:
      groups_dict = df_final[['source','score']].set_index('score').groupby(by=['source']).groups
      keys_list = list(groups_dict.keys()) #los influencers (son keys)
      mean_scores = []
      for key in keys_list:
        score_list = list(groups_dict[key]) #lista de scores
        mean_scores.append(np.mean(score_list))

      data_new = {'source':[str(key) for key in keys_list], 'score':mean_scores} #Create dataframe
      df_scores_source = pd.DataFrame(data_new).sort_values(by=['score'], ascending=False).reset_index(drop=True)

    if detailed_lists:
      return df_scores_target, df_scores_source, targets_info, sources_info
    else:
      return df_scores_target, df_scores_source
