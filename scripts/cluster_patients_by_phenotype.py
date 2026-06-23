"""
This Python file is mainly for clustering patients that are identified based on 

their parameter IDs into categories based on their phenotypic characteristics. 

It first analyzes which phenotypic traits would characterize CPM over DPM selection

for a better understanding on what kinds of phenotypes are generally being exhibited
by patients selected for CPM or DPM 



basically:

The main goal is to identify if patients with certain phenotypic characteristics 

benefit more from CPM or DPM treatment trajectory selection. 



"""





#import the dependenncies


import pandas as pd
import numpy as np

#sci kit learn clustering algorithms and some preprocessor helper methods (scaling)
from sklearn.preprocessing import StandardScaler # before k means
from sklearn.cluster import KMeans


#for files and the sqlite db
import sqlite3
import os







def analyze_phenotypes_of_the_patients(db_file, output_file, n_clusters=5):




    """


    this is the main clustering cell that will be clustering the patients based on their phenotypes (dpm input params)
    in relation to their traetment selection 

    
    the arguments would be
    
    the db_file (the path to the sqlite db locally made from bigquery), 
    
    output_file (path that you want to save the clustering results to; can be anything), 
    
    n_clusters (number of clusters, i just chose a random number below, but this is probably the most important number in terms of interprating the cluster results
    
    
    
    """




    
    # get the data from the sqlite db file path
    connection_to_sql = sqlite3.connect(db_file)
    




    #I noticed that I can't analyze cluster data that's in a time series. 
    # I'm going to average out all the different data across both treatments for each of the patients, so it has averaged-out phenotypes
    #  to be ready for clustering



    phenotype_query_for_sqlite = """


    SELECT 
        Parameter_ID,
        AVG(CAST(Drug1_dosage AS REAL)) as avg_drug1_dosage,
        AVG(CAST(Spop AS REAL)) as avg_Spop,
        AVG(CAST(R1pop AS REAL)) as avg_R1pop,
        AVG(CAST(R2pop AS REAL)) as avg_R2pop,
        AVG(CAST(R12pop AS REAL)) as avg_R12pop
    FROM Trajectories
    GROUP BY Parameter_ID


    """
    


    phenotypes = pd.read_sql(phenotype_query_for_sqlite, connection_to_sql)
    


    # This query will be used to get the survival outcomes for each of the patients
    #  and in comparison with the CPM selection and the DPM selection. 
    outcome_survival_query = """


    SELECT 
        Parameter_ID,
        AVG(CAST(Survival_CPM AS REAL)) as avg_survival_cpm,
        AVG(CAST(Survival_DPM AS REAL)) as avg_survival_dpm
    FROM ECsurvival
    GROUP BY Parameter_ID


    """
    



    #applies queries
    outcomes=pd.read_sql(outcome_survival_query, connection_to_sql)




    #close the connection to the sql db

    connection_to_sql.close()





    
    # This line will just merge the two tables together so that each patient has their final treatment outcomes too
    patient_data = phenotypes.merge(outcomes,on='Parameter_ID',how='left') #From the left 
    


    # Now I added code to calculate which strategy is actually better for each patient, 
    # in other words, the Net DPM benefit. In essence, it means that if it's a positive value, then DPM is better, and if it's a negative value, then CPM is better. 


    patient_data['DPM_benefit']=(patient_data['avg_survival_dpm']-patient_data['avg_survival_cpm']).fillna(0)
    #I noticed some of them were NaN, so I just replaced it with 0 net
    #When I merge it to the two tables, if a patient existed in the trajectories but not in ECsurvival, then there would be some NaN stuff. It would produce some errors when you calculate it if you don't replace the NaNs with 0. 



    #I am sorting it into either DPM or CPM for greater benefit based on the net benefit. 
    patient_data['better_strategy']=patient_data['DPM_benefit'].apply(lambda x:   'DPM' if x>0   else 'CPM')
    





    # This will extract all the phenotypes for clustering, so that basically just the x values
    feature_columns_list = ['avg_drug1_dosage', 'avg_Spop', 'avg_R1pop', 'avg_R2pop', 'avg_R12pop']

    X = patient_data[feature_columns_list].fillna(0).values #Again, replacing NaN with 0. 
    







    # Since k-means uses the distance calculation for clustering, it's imperative that we scale all the data to a certain range. It might heavily weigh on a certain feature if it's significantly greater in value (if we don't use a standard scaler)
    scaler = StandardScaler() # from sci kit learn
    X_scaled = scaler.fit_transform(X)






    
    # kmeans via the scikit-learn k-means clustering algorithm
    kmeans=KMeans(n_clusters=n_clusters, random_state=42, n_init=10) #42 is standard ramdomn seed, just picked 10 cuz we are doing 5 clusters (passed in as args below)

    patient_data['phenotype_cluster'] = kmeans.fit_predict(X_scaled) # pass in the normalized X
    








    #this will save results to csv
    patient_data.to_csv(output_file, index=False) #removes the index column and saves in output_file arg
    


    #return the data as well as the kmeans results

    return patient_data, kmeans





# will print the analysis for the clustering (with better verbosity). 


def print_analysis(patient_data):



    print("phenotypic clustering results:")
    
    
    print(f"\n total of {len(patient_data)} patients have been analyzed ")


    print(f"{patient_data['phenotype_cluster'].nunique()} phenotypic clusters have been made(based on argument)")
    

    #Iterates over patient_data and counts how many patients have better benefit from DPM
    number_of_patients_with_greater_dpm_benefit = (patient_data['better_strategy']=='DPM').sum()


    #same with cpm
    cpm_count=(patient_data['better_strategy']=='CPM').sum()




    print(f"\nnumber of patients with greater cpm vs. dpm benefit:")




    print(f"  Patients that favor DPM: {number_of_patients_with_greater_dpm_benefit}  ({100*number_of_patients_with_greater_dpm_benefit/len(patient_data):.1f}%)")

    print(f"  Patients that favor CPM: {cpm_count} ({100*cpm_count/len(patient_data):.1f}%)") #float conversion 
    


    print("\n") #new line




    print("Below is a cluster analysis for: which phenotypes benefit from which strategy?")



    #iter through the new clusters by id
    for cluster_id in sorted(patient_data['phenotype_cluster'].unique()):


        cluster_data = patient_data[patient_data['phenotype_cluster'] == cluster_id]


        n_patients = len(cluster_data)





        dpm_benefit = (cluster_data['better_strategy']=='DPM').sum()

        cpm_benefit = (cluster_data['better_strategy']=='CPM').sum()


        #
        dpm_percentage = 100 * dpm_benefit/n_patients
        


        print("\n")



        print(f"cluster # {cluster_id} has {n_patients} number of patients")

        



        print(f"        Selected strategy  in this specific phenotype:")



        print(f"        DPM-favored: {dpm_benefit:3d} patients ({dpm_percentage:5.1f}%)")
        print(f"        CPM-favored: {cpm_benefit:3d} patients ({100-dpm_percentage:5.1f}%)")
        
        




        """
        qualitative classification of treatment selection per cluster:
        if dpm percentage:
        
        <40 : cpm better
        >60 : dpm better
        >40 && <60 : mixed 
        """


        if dpm_percentage>60: print("strong DPM-preffering phenotype")


        elif dpm_percentage>40: print("mixed-treatment-preffering phenotype")



        else: print("strong CPM-preffering phenotype")








        print(f"\n  Phenotype traits (numbers averaged):")


        print(f"     Drug1 dosage: {cluster_data['avg_drug1_dosage'].mean():12.4f}") # mean in float 4-precision



        #Below are the means in scientific notation format (from float)
        print(f"     Spop: {cluster_data['avg_Spop'].mean():.4e}") #mean in scientific notation

        print(f"     R1: {cluster_data['avg_R1pop'].mean():.4e}")

        print(f"     R2: {cluster_data['avg_R2pop'].mean():.4e}")

        print(f"     R1-2: {cluster_data['avg_R12pop'].mean():.4e}")
        




        #I'll probably just store this in a variable/column so I don't have to calculate it twice, and it can be used a further calculation. 
        if dpm_percentage>60: print(f"     Patients in this phenotype cluster BENEFIT from DPM strategy")
        elif dpm_percentage<40: print(f"     Patients in this phenotype cluster BENEFIT from CPM strategy")
        else: print(f"     Patients in this phenotype cluster will have mixed outcomes, so the effectiveness of the strategy will vary within the cluster")
    



    print(f"\n")






#Runs all the clustering + analysis/insights code in the main method


if __name__ == '__main__':



    script_dir =os.path.dirname(os.path.abspath(__file__))


    #could use pathlib or concatenation but sticking to os.path.join for now
    db_file = os.path.join(script_dir, '../test_results.db')

    output_file = os.path.join(script_dir, '../patient_phenotype_clusters.csv')
    



    #runs clustering (preprocessing and the k-means)
    patient_data, kmeans = analyze_phenotypes_of_the_patients(db_file,output_file,n_clusters=5) # i just chose 5 clusters to start, can be changed at another time
    


    #prints interpretation
    print_analysis(patient_data)


    
    print(f"\n the results are saved to the file path: {output_file}")
