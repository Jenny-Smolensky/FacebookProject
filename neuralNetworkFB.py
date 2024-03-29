import torch.cuda
import torch.utils.data
import torch.cuda
from torch import nn, optim
from torch.autograd import Variable
from matplotlib import pyplot as plt
import torch.utils.data as data
import torch
import numpy as np

from sklearn.model_selection import StratifiedKFold, train_test_split


class FBPostData(data.Dataset):

    def __init__(self, specs, labels):
        specs = specs.astype('float32')
        self.specs = specs

        labels = torch.LongTensor(labels)
        self.classes = labels

    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: (specs, target) where target is class_index of the target class.
        """
        sample = self.specs[index]
        target = self.classes[index]

        return [sample, target]

    def __len__(self):
        return len(self.specs)


class NeuralNet(nn.Module):
    """
    this class is the model for this assignment
    """

    def __init__(self):
        super(NeuralNet, self).__init__()

        self.relu = nn.ReLU()
        self.batch_norm = nn.BatchNorm1d(12)
        self.linear1 = nn.Linear(12, 64)
        self.linear2 = nn.Linear(64, 128)
        self.linear3 = nn.Linear(128, 32)
        self.linear4 = nn.Linear(32, 5)
        self.batch_norm32 = nn.BatchNorm1d(32)
        self.batch_norm64 = nn.BatchNorm1d(64)
        self.batch_norm128 = nn.BatchNorm1d(128)

    def forward(self, x):
        x = Variable(x)
        if torch.cuda.is_available():  # use cuda if possible
            x = x.cuda()

        x = self.batch_norm(x)
        x = self.relu(self.linear1(x))
        x = self.batch_norm64(x)
        x = self.relu(self.linear2(x))
        x = self.batch_norm128(x)
        x = self.relu(self.linear3(x))
        x = self.batch_norm32(x)
        x = self.relu(self.linear4(x))

        return x


class NeuralNetworkFB:
    def __init__(self, train_data_file):

        self.data_x_train = np.loadtxt(train_data_file, skiprows=1, delimiter=';', usecols=range(0, 12))
        self.data_y_train = np.loadtxt(train_data_file, skiprows=1, delimiter=';', usecols=12)
        self.data_set_train = FBPostData(self.data_x_train, self.data_y_train)

        self.model = NeuralNet()
        if torch.cuda.is_available():
            self.model.cuda()

    def cross_validation(self, num_of_epochs=30, learning_rate=0.01,
                         l1_regular=False, l2_regular=False, reg_labmda=0.01, draw_accuracy=False):

        train_acc_cross, valid_acc_cross = [], []

        samples = self.data_set_train.specs
        tags = self.data_set_train.classes
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=3)
        cross_index = 1
        for train_index, valid_index in skf.split(samples, tags):
            train_data = FBPostData(samples[train_index], tags[train_index])
            train_loader = \
                torch.utils.data.DataLoader(train_data, batch_size=32, shuffle=True)

            validation_data = FBPostData(samples[valid_index], tags[valid_index])
            validation_loader = \
                torch.utils.data.DataLoader(validation_data, batch_size=32, shuffle=True)

            self.model = NeuralNet()  # to start training from beginning
            if torch.cuda.is_available():
                self.model.cuda()

            train_acc, valid_acc, epochs = \
                self.run_epochs(train_loader, validation_loader, num_of_epochs,
                                learning_rate, l1_regular, l2_regular, reg_labmda)
            train_acc_cross.append(max(train_acc))
            valid_acc_cross.append(max(valid_acc))

            if draw_accuracy:
                NeuralNetworkFB.draw_graph_accuracy(epochs, train_acc, valid_acc, cross_index)
                cross_index += 1

        print(f"max train accuracy: {round((max(train_acc_cross)), 3)},"
              f" max validation accuracy: {round((max(valid_acc_cross)), 3)}")
        from statistics import mean
        train_mean = round((mean(train_acc_cross)), 3)
        valid_mean = round((mean(valid_acc_cross)), 3)
        print(f"average train accuracy: {train_mean},"
              f" average validation accuracy: {valid_mean}")
        return train_mean, valid_mean

    def train(self, train_loader, learning_rate=0.001, l1_regular=False, l2_regular=False, reg_labmda=0.01):

        if torch.cuda.is_available():
            self.model.cuda()
        loss_function = nn.CrossEntropyLoss()  # set loss function
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        if l2_regular:
            optimizer.weight_decay = reg_labmda

        # go over batches
        # for specs, classes in train_loader:
        for i, (inputs, targets) in enumerate(train_loader):

            inputs = Variable(inputs)
            targets = Variable(targets)
            if torch.cuda.is_available():
                inputs = inputs.cuda()
                targets = targets.cuda()

            optimizer.zero_grad()
            output = self.model(inputs)  # get prediction
            loss = loss_function(output, targets)  # calculate loss
            if l1_regular:
                reg = 0
                for params in self.model.parameters():
                    reg += abs(0.5 * (params ** 2)).sum()
                    loss += reg_labmda * reg

            loss.backward()  # back propagation
            optimizer.step()  # optimizer step

    def evaluate(self, data_loader):
        """
        this function checks accuracy, valuate predictions from real tags
        :param data_loader: data
        :param model: model to predict with
        :return: accuracy percentage
        """
        correct = 0
        # go over data
        for (data, labels) in data_loader:
            labels = Variable(labels)
            if torch.cuda.is_available():
                labels = labels.cuda()  # use cuda if possible

            output = self.model(data)  # get prediction
            # output = torch.autograd.Variable(output, requires_grad=True)
            #  output = Variable(output)
            _, pred = torch.max(output.data, 1)  # get index of max log - probability
            correct += pred.eq(labels.view_as(pred)).cpu().sum()  # get correct in currect batch
        count_samples = len(data_loader.dataset)
        accuracy = (1. * correct / count_samples)
        return round(accuracy.item(), 3)

    def run_epochs(self, train_loader, validation_loader, num_of_epochs=100,
                   learning_rate=0.01, l1_regular=False, l2_regular=True, reg_labmda=0.01):
        train_acc = []
        valid_acc = []
        counter_for_over_fitting = 0

        for epoch in range(num_of_epochs):
            # print(f'epoch: {epoch + 1}')

            self.model.train()  # move to train mode
            self.train(train_loader, learning_rate, l1_regular, l2_regular, reg_labmda)  # train

            self.model.eval()  # move to valuation mode
            train_accuracy = self.evaluate(train_loader)  # valuate
            train_acc.append(train_accuracy)
            # print(f"train set accuracy: {train_accuracy}")

            valid_accuracy = self.evaluate(validation_loader)
            # print(f"validation set accuracy: {valid_accuracy}")
            valid_acc.append(valid_accuracy)

            # if train_accuracy - valid_accuracy > 0.05:
            #     counter_for_over_fitting += 1
            #     if counter_for_over_fitting > 5:
            #         break

        return train_acc, valid_acc, epoch + 1  # if want to print

    def draw_graph_accuracy(num_of_epochs, train_accuracy, validation_accuracy, file_index=0):
        """
        this function creates graph of train and validation accuracy per epoch
        :param num_of_epochs:
        :param train_accuracy:
        :param validation_accuracy:
        :return: none
        """
        plt.clf()
        x = list(range(1, num_of_epochs + 1))
        plt.plot(x, validation_accuracy, label="validation", color='blue', linewidth=2)
        plt.plot(x, train_accuracy, label="train", color='green', linewidth=2)
        plt.title('Accuracy per epoch', fontweight='bold', fontsize=13)
        plt.xlabel('number of epoch')
        plt.ylabel('accuracy')
        plt.legend()
        plt.show()
        file_name = f"net-accuracy{file_index}.png"
        plt.savefig(file_name)

    @property
    def check_hyper_parameters(self):
        learn_rate = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
        lamdba_reg = [0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
        epochs = [10, 20, 30, 50, 100]
        parms = []
        train = []
        valid = []
        all_combinations = [[i, j, k, True, False] for i in learn_rate
                            for j in lamdba_reg
                            for k in epochs]
        all_combinations.extend([[i, j, k, False, True] for i in learn_rate
                                 for j in lamdba_reg
                                 for k in epochs])

        for lr, lamdba_reg, epochs, l1_reg, l2_reg in all_combinations:
            print(f"lr: {lr}, lamda: {lamdba_reg}, epochs: {epochs}, l1: {l1_reg}, l2: {l2_reg}")
            mean_train, mean_valid = self.cross_validation(epochs, lr, l1_reg, l2_reg, lamdba_reg)
            parms.append([lr, lamdba_reg, epochs, l1_reg, l2_reg])
            train.append(mean_train)
            valid.append(mean_valid)

        best_index = valid.index(max(valid))
        best_params = parms[best_index]
        print(f"best in: lr={best_params[0]}, lambda={best_params[1]}, epochs={best_params[2]},"
              f" l1_reg={best_params[3]}, l2_reg={best_params[4]} \n"
              f" train accuracy={train[best_index]}, valid accuracy={valid[best_index]}")
        dict_best = {
            "lr": best_params[0],
            "lambda": best_params[1],
            "epochs": best_params[2],
            "l1": best_params[3],
            "l2": best_params[4]}

        return dict_best

    def check_hyper_parameters_no_reg(self):
        learn_rate = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
        epochs = [10, 20, 30, 50, 100]

        all_combinations = [[i, j] for i in learn_rate for j in epochs]
        parms_no_reg = []
        train_no_reg, valid_no_reg = [], []
        for lr, epochs in all_combinations:
            print(f"lr: {lr}, epochs: {epochs}")
            mean_train, mean_valid = self.cross_validation(epochs, lr, False, False)
            parms_no_reg.append([lr, epochs])
            train_no_reg.append(mean_train)
            valid_no_reg.append(mean_valid)

        best_index_no_reg = valid_no_reg.index(max(valid_no_reg))
        best_params_no_reg = parms_no_reg[best_index_no_reg]
        print(f"best in: lr={best_params_no_reg[0]}, epochs={best_params_no_reg[1]}, \n "
              f"train accuracy={train_no_reg[best_index_no_reg]}, valid accuracy={valid_no_reg[best_index_no_reg]}")

    def train_model_and_check_validation(self, epochs, lr, l1_reg, l2_reg, lambda_reg, draw_accuracy=True):
        train_acc_cross, valid_acc_cross = [], []

        validation_split = .2
        data_set_size = len(self.data_set_train)
        indices = list(range(data_set_size))
        split = int(np.floor(validation_split * data_set_size))
        train_index, valid_index = indices[split:], indices[:split]
        samples = self.data_set_train.specs
        tags = self.data_set_train.classes

        train_data = FBPostData(samples[train_index], tags[train_index])
        train_loader = \
            torch.utils.data.DataLoader(train_data, batch_size=32, shuffle=True)

        validation_data = FBPostData(samples[valid_index], tags[valid_index])
        validation_loader = \
            torch.utils.data.DataLoader(validation_data, batch_size=32, shuffle=True)

        self.model = NeuralNet()  # to start training from beginning
        if torch.cuda.is_available():
            self.model.cuda()

        train_acc, valid_acc, epochs = \
            self.run_epochs(train_loader, validation_loader, epochs, lr, l1_reg, l2_reg, lambda_reg)
        train_acc_cross.append(max(train_acc))
        valid_acc_cross.append(max(valid_acc))

        if draw_accuracy:
            NeuralNetworkFB.draw_graph_accuracy(epochs, train_acc, valid_acc)

    def train_model(self, epochs, lr, l1_reg, l2_reg, lambda_reg):

        # validation_split = .2
        # data_set_size = len(self.data_set_train)
        # indices = list(range(data_set_size))
        # split = int(np.floor(validation_split * data_set_size))
        # train_indices, val_indices = indices[split:], indices[:split]
        # samples = self.data_set_train.specs
        # tags = self.data_set_train.classes
        print('training neural network model')
        train_data = self.data_set_train
        train_loader = \
            torch.utils.data.DataLoader(train_data, batch_size=32, shuffle=True)
        # this time train with the whole train set
        validation_loader = \
            torch.utils.data.DataLoader(train_data, batch_size=32, shuffle=True)
        self.model = NeuralNet()
        train_acc, valid_acc, epoch = self.run_epochs(train_loader, validation_loader, epochs, lr, l1_reg, l2_reg,
                                                      lambda_reg)
        print(f"train accuracy: {train_acc[-1]}")

    def predict_test(self, test_data_file):

        data_x_test = np.loadtxt(test_data_file, skiprows=1, delimiter=';', usecols=range(0, 12))
        data_y_test = np.loadtxt(test_data_file, skiprows=1, delimiter=';', usecols=12)

        data_set_test = FBPostData(data_x_test, data_y_test)
        test_loader = \
            torch.utils.data.DataLoader(data_set_test, batch_size=32, shuffle=False)

        self.model.eval()
        success_rate = self.evaluate(test_loader)
        print(f"accuracy on test set: {success_rate}")
        return success_rate

    def predict_sample_tag(self, sample):

        self.model.eval()
        sample = torch.FloatTensor(sample)
        sample = torch.reshape(sample, (1, len(sample)))
        output = self.model(sample)  # get prediction
        output = torch.autograd.Variable(output, requires_grad=True)
        output = output.max(1, keepdim=True)[1]  # get index of max log - probability

        return output.item()
