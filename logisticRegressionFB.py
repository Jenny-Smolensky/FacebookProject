from sklearn.linear_model import LogisticRegression
import pandas as pd
from sklearn import metrics
from sklearn.model_selection import StratifiedKFold
import csv
import numpy as np


class LogisticRegressionFB:

    def __init__(self, data_file):
        with open(data_file, 'r') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
        col_names = fieldnames[0].split(';')
        # load dataset
        pima = pd.read_csv(data_file, skiprows=1, header=None, delimiter=';', names=col_names)
        pima.head()
        # split dataset in features and target variable
        feature_cols = col_names[:-1]
        self.data_features = pima[feature_cols]  # Features
        self.data_tags = pima.like  # Target variable
        self.model = None

    def cross_validation(self, c_value=100000000000000000, solver='lbfgs', max_iter=100):
        train_acc_cross, valid_acc_cross = [], []
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=3)
        data_features = np.array(self.data_features)
        data_tags = np.array(self.data_tags)

        for train_index, valid_index in skf.split(data_features, data_tags):
            train_data = data_features[train_index]
            train_tags = data_tags[train_index]

            validation_data = data_features[valid_index]
            validation_tags = data_tags[valid_index]

            logreg = LogisticRegression(penalty='l2', C=c_value, solver=solver, max_iter=max_iter,
                                        multi_class='multinomial')

            # Train Logistic regression Tree Classifer
            logreg = logreg.fit(train_data, train_tags)

            # Predict the response for test dataset
            validation_predictions = logreg.predict(validation_data)
            train_predictions = logreg.predict(train_data)

            train_acc_cross.append(metrics.accuracy_score(train_tags, train_predictions))
            valid_acc_cross.append(metrics.accuracy_score(validation_tags, validation_predictions))

        print(f"max train accuracy: {round((max(train_acc_cross)).item(), 3)},"
              f" max validation accuracy: {round((max(valid_acc_cross)).item(), 3)}")
        from statistics import mean

        train_mean = round((mean(train_acc_cross)).item(), 3)
        valid_mean = round((mean(valid_acc_cross)).item(), 3)
        print(f"average train accuracy: {train_mean},"
              f" average validation accuracy: {valid_mean}")
        return train_mean, valid_mean

    def check_hyper_parameters(self):
        c_value = [0.01, 0.1, 1, 10, 100, 1000, 10000]
        solver = ['newton-cg', 'lbfgs', 'sag', 'saga']
        max_iter = [100, 1000, 100000, 1000000]

        parms = []
        train = []
        valid = []
        all_combinations = [[j, k, z]
                            for j in c_value
                            for k in solver
                            for z in max_iter]

        for c_value, solver, max_iter in all_combinations:
            print(f"C: {c_value}, solver: {solver}, max_iter: {max_iter}")
            mean_train, mean_valid = self.cross_validation(c_value, solver, max_iter)
            parms.append([c_value, solver, max_iter])
            train.append(mean_train)
            valid.append(mean_valid)

        best_index = valid.index(max(valid))
        best_params = parms[best_index]
        print(f"best in: C={best_params[0]}, solver={best_params[1]},"
              f"max_iter={best_params[2]} \n"
              f" train accuracy={train[best_index]}, valid accuracy={valid[best_index]}")
        dict_best = {
            "c": best_params[0],
            "solver": best_params[1],
            "max_iter": best_params[2]}
        return dict_best

    def train_logistic_regression(self, c_value=100000000000000000, solver='lbfgs', max_iter=100):
        print('training logistic regression model')
        self.model = LogisticRegression(penalty='l2', C=c_value, solver=solver, max_iter=max_iter,
                                        multi_class='multinomial')
        self.model = self.model.fit(self.data_features, self.data_tags)

    def draw_training_samples(samples, train_accuracy, validation_accuracy):
        """
        this function creates graph of train and validation accuracy per epoch
        :param num_of_epochs:
        :param train_accuracy:
        :param validation_accuracy:
        :return: none
        """
        from matplotlib import pyplot as plt
        plt.clf()
        plt.plot(samples, validation_accuracy, label="validation", color='blue', linewidth=2)
        plt.plot(samples, train_accuracy, label="train", color='green', linewidth=2)
        plt.title('Accuracy as function of training samples', fontweight='bold', fontsize=13)
        plt.xlabel('training samples')
        plt.ylabel('accuracy')
        plt.legend()
        plt.show()
        file_name = f"logistic-accuracy.png"
        plt.savefig(file_name)

    def train_by_samples(self, c_value=100000000000000000, solver='lbfgs', max_iter=100):

        validation_split = .2
        data_set_size = len(self.data_features)
        indices = list(range(data_set_size))
        split = int(np.floor(validation_split * data_set_size))
        train_index, valid_index = indices[split:], indices[:split]
        data_features = np.array(self.data_features)
        data_tags = np.array(self.data_tags)

        train_data = data_features[train_index]
        train_tags = data_tags[train_index]

        validation_data = data_features[valid_index]
        validation_tags = data_tags[valid_index]

        ######FOR SPLITTING DATA TO ERROR GRAPH####
        split_logreg = LogisticRegression(penalty='l2', C=c_value, solver=solver, max_iter=max_iter,
                                          multi_class='multinomial')

        train_split_acc, valid_split_acc, samples_train = [], [], []

        d1, d2, d3, d4, d5, d6, d7, d8, d9, d10 = np.array_split(train_data, 10)
        t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = np.array_split(train_tags, 10)

        d = [d1, d2, d3, d4, d5, d6, d7, d8, d9, d10]
        t = [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10]


        for split_index in range(0, 10):
            train_split_data = np.concatenate((d[0:(split_index + 1)]), axis=0)
            train_split_tags = np.concatenate((t[0:(split_index + 1)]), axis=0)

            split_logreg = LogisticRegression(penalty='l2', C=c_value, solver=solver, max_iter=max_iter,
                                              multi_class='multinomial')

            # Train Logistic regression Tree Classifer
            split_logreg = split_logreg.fit(train_split_data, train_split_tags)

            # Predict the response for test dataset
            valid_predictions = split_logreg.predict(validation_data)
            train_part_predictions = split_logreg.predict(train_split_data)

            train_split_acc.append(metrics.accuracy_score(train_split_tags, train_part_predictions))
            valid_split_acc.append(metrics.accuracy_score(validation_tags, valid_predictions))
            samples_train.append(len(train_split_tags))

        LogisticRegressionFB.draw_training_samples(samples_train, train_split_acc, valid_split_acc)

    def predict_test(self, test_data_file):
        data_x_test = np.loadtxt(test_data_file, skiprows=1, delimiter=';', usecols=range(0, 12))
        data_y_test = np.loadtxt(test_data_file, skiprows=1, delimiter=';', usecols=12)

        y_pred = self.model.predict(data_x_test)
        accuracy = metrics.accuracy_score(data_y_test, y_pred)
        accuracy = round(accuracy, 3)

        y_pred_train = self.model.predict(self.data_features)
        accuracy_train = metrics.accuracy_score(self.data_tags, y_pred_train)
        accuracy_train = round(accuracy_train, 3)
        print(f"train accuracy: {accuracy_train} accuracy on test set: {accuracy}")

        return accuracy

    def predict_sample(self, sample):
        sample = np.reshape(sample, (1, len(sample)))
        output = self.model.predict(sample)
        return output.item()
