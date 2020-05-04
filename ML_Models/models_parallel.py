import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.model_selection import GridSearchCV
from sklearn import linear_model
from sklearn import svm
import tensorflow as tf
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from multiprocessing import Process
from pexecute.process import ProcessLoom
import time
from sys import argv


########################################################## SVM-poly
def SVM(X_train, X_test, y_train):

    svmModelObject = svm.SVC(kernel = 'poly')
    svmModelObject.fit(X_train, y_train)
    y_prediction = svmModelObject.predict(X_test)

    return y_prediction
####################################################### GBM
def GBM(X_train, X_test, y_train):
    parameters = {'n_estimators': 500, 'max_depth': 4, 'min_samples_split': 2,
                  'learning_rate': 0.01, 'loss': 'ls'}
    GradientBoostingRegressorObject = GradientBoostingRegressor(**parameters)

    GradientBoostingRegressorObject.fit(X_train, y_train)
    y_prediction = GradientBoostingRegressorObject.predict(X_test)

    return y_prediction


###################################################### GLM
def GLM(X_train, X_test, y_train):
    alpha = 0.1
    GLM_Model = linear_model.Lasso(alpha=alpha)
    GLM_Model.fit(X_train, y_train)
    y_prediction = GLM_Model.predict(X_test)

    return y_prediction


####################################################### KNN
def KNN(X_train, X_test, y_train):
    KNeighborsRegressorObject = KNeighborsRegressor()
    # Grid search over different Ks to choose the best one
    parameters = {'n_neighbors': [5, 10, 15, 20, 25, 30, 40, 50]}
    GridSearchOnKs = GridSearchCV(KNeighborsRegressorObject, parameters, cv=5)
    GridSearchOnKs.fit(X_train, y_train)
    best_K = GridSearchOnKs.best_params_
    # train KNN with the best K
    KNN_Model = KNeighborsRegressor(n_neighbors=best_K['n_neighbors'])
    KNN_Model.fit(X_train, y_train)
    y_prediction = KNN_Model.predict(X_test)

    return y_prediction


####################################################### NN
def NN(X_train, X_test, y_train, y_test):
    scaler = MinMaxScaler()  # For normalizing dataset

    X_train_scaled = scaler.fit_transform(X_train)
    y_train_scaled = scaler.fit_transform(y_train.reshape(-1, 1))
    X_test_scaled = scaler.fit_transform(X_test)
    y_test_scaled = scaler.fit_transform(y_test.reshape(-1, 1))

    def denormalize(main_data, normal_data):

        main_data = main_data.reshape(-1, 1)
        normal_data = normal_data.reshape(-1, 1)
        scaleObject = MinMaxScaler()
        scaleMain = scaleObject.fit_transform(main_data)
        denormalizedData = scaleObject.inverse_transform(normal_data)

        return denormalizedData

    def neural_net_model(X_data, input_dim):  # a 1-layer NN

        # layer 1 multiplying and adding bias and activation function
        W_1 = tf.Variable(tf.random_uniform([input_dim, 10]))
        b_1 = tf.Variable(tf.zeros([10]))
        layer_1 = tf.add(tf.matmul(X_data, W_1), b_1)
        layer_1 = tf.nn.relu(layer_1)
        # output layer
        W_O = tf.Variable(tf.random_uniform([10, 1]))
        b_O = tf.Variable(tf.zeros([1]))
        output = tf.add(tf.matmul(layer_1, W_O), b_O)
        # output layer multiplying and adding bias then activation function
        # notice output layer has one node only since performing #regression
        return output

    xPlaceHolder = tf.placeholder("float")
    yPlaceHolder = tf.placeholder("float")
    output = neural_net_model(xPlaceHolder, X_train.shape[1])
    # our mean squared error cost function
    cost = tf.reduce_mean(tf.square(output - yPlaceHolder))
    # Gradinent Descent optimiztion for updating weights and biases
    train = tf.train.GradientDescentOptimizer(0.001).minimize(cost)

    with tf.Session() as sess:
        # Initiate session and initialize all vaiables
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()

        results_train = []
        results_test = []
        for i in range(10):
            for j in range(X_train_scaled.shape[0]):
                sess.run([cost, train],
                         feed_dict={xPlaceHolder: X_train_scaled[j, :].reshape(1, X_train.shape[1]), yPlaceHolder: y_train_scaled[j]})
                # Run cost and train with each sample
            results_train.append(sess.run(cost, feed_dict={xPlaceHolder: X_train_scaled, yPlaceHolder: y_train_scaled}))
            results_test.append(sess.run(cost, feed_dict={xPlaceHolder: X_test_scaled, yPlaceHolder: y_test_scaled}))
            print('Epoch :', i, 'Cost :', results_train[i])

        # predict output of test data after training
        y_prediction = sess.run(output, feed_dict={xPlaceHolder: X_test_scaled})

        print('Cost :', sess.run(cost, feed_dict={xPlaceHolder: X_test_scaled, yPlaceHolder: y_test_scaled}))
        # Denormalize data
        # y_test_denormalized = denormalize(y_test, y_test_scaled)
        y_prediction = denormalize(y_test, y_prediction)

    return y_prediction


########################################################## MM-LR
def MM_LR(X_train, X_test, y_train):
    # fit a linear regression model on the outputs of the other models
    regressionModelObject = linear_model.LinearRegression()
    regressionModelObject.fit(X_train, y_train)
    y_prediction = regressionModelObject.predict(X_test)

    return y_prediction
 
########################################################## data preprocessing
def preprocess(path):
    # loading the dataset
    data = pd.read_csv(path)
    data = pd.DataFrame(data)
    main_data = data.drop(['FIPS code', 'STATE', 'row number of train sample for county', 'current day(t)',
                           'target number of confirmed case', 'COUNTY', 'STNAME', 'CTYNAME'], axis=1)
    target = pd.DataFrame(data['target number of confirmed case'])

    numberOfCounties = len(data['FIPS code'].unique())
    numberOfDays = data.shape[0] / numberOfCounties
    train_offset = int((3 * numberOfDays)/4)
    test_offset = int(numberOfDays - train_offset)
    X_train = pd.DataFrame()
    X_test = pd.DataFrame()
    y_train = pd.DataFrame()
    y_test = pd.DataFrame()

    # select the first 3/4 of days for training and the rest of them for testing 
    for i in range(numberOfCounties + 1):
        j = i * numberOfDays
        X_train = X_train.append(main_data.loc[j:j+train_offset-1])
        y_train = y_train.append(target.loc[j:j+train_offset-1])
        j = j + train_offset
        X_test = X_test.append(main_data.loc[j:j+test_offset-1])
        y_test = y_test.append(target.loc[j:j+test_offset-1])

    X_train = X_train.reset_index(drop=True)
    X_test = X_test.reset_index(drop=True)
    y_train = np.array(y_train).reshape(-1)
    y_test = np.array(y_test).reshape(-1)

    return X_train, X_test, y_train, y_test


#####################################################################
if __name__ == "__main__":

    path = argv[1]
    X_train, X_test, y_train, y_test = preprocess(path)

    t1 = time.time()
    loom = ProcessLoom(max_runner_cap=10)
    # add the functions to the multiprocessing object, loom
    loom.add_function(GBM, [X_train, X_test, y_train], {})
    loom.add_function(GLM, [X_train, X_test, y_train], {})
    loom.add_function(KNN, [X_train, X_test, y_train], {})
    loom.add_function(NN, [X_train, X_test, y_train, y_test], {})
    # run the processes in parallel
    output = loom.execute()
    t2 = time.time()
    print('total time: ', t2 - t1)
    # print(output[0]['execution_time'], output[1]['execution_time'], output[2]['execution_time']
    # ,output[3]['execution_time'])

    # get the outputs
    y_prediction_GBM = output[0]['output']
    y_prediction_GLM = output[1]['output']
    y_prediction_KNN = output[2]['output']
    y_prediction_NN = output[3]['output']
    y_prediction_NN = np.array(y_prediction_NN).reshape(-1)
    y_predictions = []
    # Construct the outputs for the training dataset of the 'MM' methods
    y_predictions.extend([y_prediction_GBM, y_prediction_GLM, y_prediction_KNN, y_prediction_NN])
    y_prediction_np = np.array(y_predictions).reshape(len(y_predictions), -1)
    X_mixedModel = pd.DataFrame(y_prediction_np.transpose())
    X_train_MM, X_test_MM, y_train_MM, y_test_MM = train_test_split(X_mixedModel, y_test, test_size=0.25)
    # run mixed model with linear regression
    y_prediction_MM_LR = MM_LR(X_train_MM, X_test_MM, y_train_MM)
    # run mixed model with neural network
    y_prediction_MM_NN = NN(X_train_MM, X_test_MM, y_train_MM, y_test_MM)

    mse = mean_squared_error(y_test, y_prediction_GBM)
    print("MSE of GBM: %.4f" % mse)
    mse = mean_squared_error(y_test, y_prediction_GLM)
    print("MSE of GLM: %.4f" % mse)
    mse = mean_squared_error(y_test, y_prediction_KNN)
    print("MSE of KNN: %.4f" % mse)
    mse = mean_squared_error(y_test, y_prediction_NN)
    print("MSE of NN: %.4f" % mse)
    mse = mean_squared_error(y_test_MM, y_prediction_MM_LR)
    print("MSE of MM-LR: %.4f" % mse)
    mse = mean_squared_error(y_test_MM, y_prediction_MM_NN)
    print("MSE of MM-NN: %.4f" % mse)






