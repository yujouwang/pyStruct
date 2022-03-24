import pickle
import numpy as np
from typing import Protocol

from sklearn.preprocessing import MinMaxScaler
from sklearn import ensemble
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from sklearn.inspection import permutation_importance
from scipy.stats import halfcauchy, norm
import matplotlib.pyplot as plt

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import arviz as az 
import pymc3 as pm
import scipy.stats as stats
from theano import shared
from sklearn.preprocessing import StandardScaler





class VisualizeOptimization:
    def __init__(self, config, ncols=5):
        self.config = config
        self.wp = self._init_data(config)

        # plot setting
        self.ncols=5
        self.N_samples = config['N_samples']
        self.nrows = ceil(self.N_samples/self.ncols)

    def _init_data(self, config):
        wp_path = config['save_to']/'ts_regression'/'wp.csv'
        wp = pd.read_csv(wp_path)
        return wp

    def read_weights_from_table(self, theta_deg, samples):
        wp = self.wp
        weights ={}
        for sample in samples:
            weights[sample] = []
            wp_sub = wp[(wp['theta_deg']==theta_deg) & (wp['sample']==sample)]
            for mode in range(self.config['N_modes']):
                w = wp_sub[wp_sub['mode']==mode].w.iloc[0]
                weights[sample].append(w)
        
        return weights


    
    def plot_T_probe(self, theta_deg, weights, figsize=(16, 12)):
        # get xy
        self.config['theta_deg'] = theta_deg
        ts = TimeSeriesPredictor(
            N_samples=self.config['N_samples'], 
            N_modes=self.config['N_modes'], 
            N_t=self.config['N_t'], 
            wp=self.wp
        )
        X, y, idx = ts.get_training_pairs(self.config)

        # Plot 
        fig_1, axes_1 = plt.subplots(nrows=self.nrows, ncols=self.ncols, figsize=figsize)
        fig_2, axes_2 = plt.subplots(nrows=self.nrows, ncols=self.ncols, figsize=figsize)


        for sample in weights.keys():
            ax_1 = axes_1[sample//self.ncols, sample%self.ncols]
            ax_2 = axes_2[sample//self.ncols, sample%self.ncols]

            # predict 
            ax_1.set_title(sample)
            y_pred = np.array(
                    [X[sample, mode, :] * weights[sample][mode] for mode in range(self.config['N_modes']) ] ).sum(axis=0)
            ax_1.plot(y[sample][-self.config['N_t']:], label='True')
            ax_1.plot(y_pred, label='Pred')

            # Ax2 : Stem
            all_weights = np.zeros(self.N_samples)
            for i, id in enumerate(idx[sample]):
                all_weights[id] = weights[sample][i]
            ax_2.stem(all_weights)
            ax_2.set_xticks(np.arange(len(idx[sample])))
            ax_2.set_xticklabels(idx[sample])
        plt.show()

        fig_1.savefig(self.config['save_to']/'figures'/f'optm_pred_theta_{theta_deg}.png')
        fig_2.savefig(self.config['save_to']/'figures'/f'optm_w_theta_{theta_deg}.png')


def plot_regression_deviance(reg, params, X_test_norm, y_test):
    test_score = np.zeros((params["n_estimators"],), dtype=np.float64)
    for i, y_pred in enumerate(reg.staged_predict(X_test_norm)):
        test_score[i] = reg.loss_(y_test, y_pred)

    fig = plt.figure(figsize=(6, 6))
    plt.subplot(1, 1, 1)
    plt.title("Deviance")
    plt.plot(
        np.arange(params["n_estimators"]) + 1,
        reg.train_score_,
        "b-",
        label="Training Set Deviance",
    )
    plt.plot(
        np.arange(params["n_estimators"]) + 1, test_score, "r-", label="Test Set Deviance"
    )
    plt.legend(loc="upper right")
    plt.xlabel("Boosting Iterations")
    plt.ylabel("Deviance")
    fig.tight_layout()
    plt.show(block=False)

def plot_feature_importance(reg, feature_names, X_test_norm, y_test):

    feature_importance = reg.feature_importances_
    sorted_idx = np.argsort(feature_importance)
    pos = np.arange(sorted_idx.shape[0]) + 0.5
    fig = plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.barh(pos, feature_importance[sorted_idx], align="center")
    plt.yticks(pos, np.array(feature_names)[sorted_idx])
    plt.title("Feature Importance (MDI)")

    result = permutation_importance(
        reg, X_test_norm, y_test, n_repeats=10, random_state=42, n_jobs=2
    )
    sorted_idx = result.importances_mean.argsort()
    plt.subplot(1, 2, 2)
    plt.boxplot(
        result.importances[sorted_idx].T,
        vert=False,
        labels=np.array(feature_names)[sorted_idx],
    )
    plt.title("Permutation Importance (test set)")
    fig.tight_layout()
    plt.show(block=False)

def plot_weights_accuracy_scatter(reg, X_train_norm, y_train, X_test_norm, y_test):

    fig, axes = plt.subplots(nrows=1, ncols=2)
    ax = axes[0]
    y_pred = reg.predict(X_train_norm)
    y_true = y_train
    ax.scatter(y_true, y_pred)
    ax.plot([-3,2], [-3,2], 'k')
    ax.set_title("Train")

    ax = axes[1]
    y_pred = reg.predict(X_test_norm)
    y_true = y_test
    ax.scatter(y_true, y_pred)
    ax.plot([-3,2], [-3,2], 'k')
    ax.set_title("Test")
    plt.show(block=False)


def gb_regression(params, X_train, y_train, X_test, y_test, feature_names, show=False):
    # Normalize the features 
    norm = MinMaxScaler().fit(X_train.to_numpy())
    X_train_norm = norm.transform(X_train.to_numpy())
    X_test_norm = norm.transform(X_test.to_numpy())


    reg = ensemble.GradientBoostingRegressor(**params)
    reg.fit(X_train_norm, y_train)
    error = mean_squared_error(y_test, reg.predict(X_test_norm))
    print(f"Regression mean squre error: {error}")
    if show:
        plot_regression_deviance(reg, params, X_test_norm, y_test)
        plot_feature_importance(reg, feature_names, X_test_norm, y_test)
        plot_weights_accuracy_scatter(reg, X_train_norm, y_train, X_test_norm, y_test)
    return reg, norm



def split_mode_traintest(wp_mode, train_ratio):
    N_s = len(wp_mode)
    wp_train = wp_mode.iloc[:int(train_ratio*N_s)]
    wp_test = wp_mode.iloc[int(train_ratio*N_s):]
    return wp_train, wp_test


def get_regressors_for_each_mode(N_modes, params, wp, feature_names, train_ratio=1, show=False):
    regs = []
    norms = []
    for mode in range(N_modes):
        print(f"---regression mode:{mode}---")
        wp_mode = wp[wp['mode'] == mode]
        wp_train, wp_test = split_mode_traintest(wp_mode.sample(frac=1), train_ratio)
        print(wp_train)

        # Prepare train and test
        X_train = wp_train[feature_names]
        y_train = wp_train['w']
        X_test = wp_test[feature_names]
        y_test = wp_test['w']

        reg, norm = gb_regression(params, X_train, y_train, X_test, y_test, feature_names, show)
        regs.append(reg)
        norms.append(norm)
    
    if show:
        plt.show(block=True)
    return regs, norms

def wp_split_train_test(feature_table, train_id, feature_labels, target_label):
    bool_series = feature_table['sample'].isin(train_id)
    table_train = feature_table[bool_series]
    table_test = feature_table[bool_series==False]
    X_train = table_train[feature_labels]
    y_train = table_train[target_label]
    X_test = table_test[feature_labels]
    y_test = table_test[target_label]
    return X_train, y_train, X_test, y_test

class WeightsPredictor(Protocol):
    def train(self):
        pass
    def predict(self):
        pass
    def load(self):
        pass


class GbRegressor:
    def __init__(self, config):
        self.config = config
        self.params = {
            "n_estimators": 1000,
            "max_depth":10,
            "min_samples_split": 2,
            "learning_rate": 0.005,
            "loss": "squared_error",
        }
        self.save_folder = Path(self.config['save_to']) / 'weights_predictor'
        self.save_folder.mkdir(parents=True, exist_ok=True)
        self.save_as = self.save_folder / "gb_regressor.pkl"
    
    def train(self, feature_table, show=False):
        self.regs = []
        self.norms = []
        for mode in range(self.config['N_modes']):
            f = feature_table[feature_table['mode'] == mode]
            X_train, y_train, X_test, y_test = wp_split_train_test(
                f,
                self.config['training_id'],
                self.config['y_labels'],
                ['w'])


            norm = MinMaxScaler().fit(X_train.to_numpy())
            X_train_norm = norm.transform(X_train.to_numpy())
            X_test_norm = norm.transform(X_test.to_numpy())


            reg = ensemble.GradientBoostingRegressor(**self.params)
            reg.fit(X_train_norm, y_train)
            error = mean_squared_error(y_test, reg.predict(X_test_norm))
            print(f"Regression mean squre error: {error}")

            self.regs.append(reg)
            self.norms.append(norm)

            if show:
                # plot_regression_deviance(reg, self.params, X_test_norm, y_test)
                # plot_feature_importance(reg, feature_names, X_test_norm, y_test)
                plot_weights_accuracy_scatter(reg, X_train_norm, y_train, X_test_norm, y_test)

        # Save 
        with open(self.save_as, 'wb') as f:
            pickle.dump((self.regs, self.norms), f)
        return feature_table
    
    def load(self, feature_table):
        print("load file")
        with open(self.save_as, 'rb') as f:
            self.regs, self.norms = pickle.load(f)
        return


    def predict(self, features: np.ndarray):
        assert hasattr(self, 'regs'), "No regressors exist. Train or Read first"
        assert features.shape == (self.config['N_modes'], len(self.config['y_labels']))
            
        weights=[]
        for mode in range(self.config['N_modes']):
            reg = self.regs[mode]
            norm = self.norms[mode]
            # normalize the feature
            normalized_feature_mode = norm.transform(features)[mode, :]
            weights.append(reg.predict(normalized_feature_mode.reshape(1,len(self.config['y_labels']))))
        return weights

    
class BayesianModel:
    def __init__(
        self, 
        config:dict,
        ):
        self.config = config
        self.var_names = config['y_labels']
        self.target_name = 'w'

        self.save_folder = Path(config['save_to'])/f"bayesian_model"
        self.save_folder.mkdir(parents=True, exist_ok=True)
        self.save_as = self.save_folder/"idata.nc"

    def _init_data(self, feature_table):

        # get data
        self.feature_table = feature_table
        self.target = self.feature_table[self.target_name].values
        self.inputs = {}
        self.inputs_shared={}
        self.standrdizers = {}
        for var_name in self.var_names:
            input, standrdizer = self.transform_input(var_name)
            self.inputs_shared[var_name] = shared(input) # the shared tensor, which can be modified later
            self.standrdizers[var_name] = standrdizer
            self.inputs[var_name] = input # this won't change

    def build_model(self):
        with pm.Model() as model:
            # Hyperpriors for group nodes
            eps = pm.HalfCauchy("eps", 4)
            a = pm.Normal('a', mu=0.5, sd=1)
            mu = a
            for i, var_name in enumerate(self.var_names):
                b_i = pm.Normal(var_name, mu = -1.1, sd= 5 )
                mu = a + b_i * self.inputs_shared[var_name]
            w = pm.Normal( "w", mu=mu, sigma=eps, observed=self.target)
        self.model = model
        return

    def transform_input(self, var_name):
        standardizer = StandardScaler()
        var = standardizer.fit_transform(self.feature_table[var_name].values.reshape(-1,1)).flatten()
        return var, standardizer
    
    def train(self, feature_table, show=False, samples=1000):
        """ Inference """
        self._init_data(feature_table)
        self.build_model()
        with self.model:
            # step = pm.NUTS(target_accept=0.95)
            idata = pm.sample(samples, tune=1000, return_inferencedata=True, chains=1)
        self.idata = idata
        idata.to_netcdf(self.save_as)
        with open(self.save_folder / "standardizer.pkl", 'wb') as f:
            pickle.dump(self.standrdizers, f)
        return 

    def load(self, feature_table):
        print("load Bayesian weights predictor")
        self._init_data(feature_table)
        self.build_model()
        self.idata = az.from_netcdf(self.save_folder/"idata.nc")
        with open(self.save_folder / "standardizer.pkl", 'rb') as f:
            self.standrdizers = pickle.load(f)
        return

    def predict(self, features):
        assert features.shape == (self.config['N_modes'], len(self.config['y_labels']))
        # features = features.to_numpy()

        df = az.summary(self.idata)

        # Get the mean value
        a = df.loc['a', 'mean']
        weights =[]
        for mode in range(self.config['N_modes']):
            w_preds = a
            for i, var_name in enumerate(self.var_names):
                b_i = df.loc[var_name, 'mean']
                w_preds += b_i*self.standrdizers[var_name].transform(features[mode, i].reshape(-1, 1))
            
            weights.append(w_preds[0])
        return weights
    def sampling(self, features, N_realizations=100):
        df = az.summary(self.idata)

        # Get the mean value
        sigma = df.loc['eps', 'mean']
        a = df.loc['a', 'mean']
        weights_samples =[]
        for mode in range(self.config['N_modes']):
            mu = a
            for i, var_name in enumerate(self.var_names):
                b_i = df.loc[var_name, 'mean']
                mu += b_i*self.standrdizers[var_name].transform(features[mode, i].reshape(-1, 1))

            w_preds = norm.rvs(loc=mu, scale=sigma, size=(1,N_realizations))
            weights_samples.append(w_preds)
        return weights_samples

    def counterfactual_plot(self, x, cvar_name, N_samples=100):
        assert len(x) == len(self.target)

        # set control variable
        self.inputs_shared[cvar_name].set_value(x) 

        print("Sample posterior...")
        with self.model:
            post_pred = pm.sample_posterior_predictive(self.idata.posterior)
        print("Done")

        # plot the hdi of the prediction scatter
        _, ax = plt.subplots()
        az.plot_hdi(x, post_pred['w'])
        ax.plot(x, post_pred['w'].mean(0))
        ax.scatter(self.inputs[cvar_name], self.target)
        plt.show()

    def validation(self, config):
        df = az.summary(self.idata)
        # Get the mean value
        a = df.loc['a', 'mean']
        w_preds = a
        for var_name in self.var_names:
            b_i = df.loc[var_name, 'mean']
            # w_preds += b_i*self.standrdizers[var_name].transform(self.inputs[var_name])
            w_preds += b_i*self.inputs[var_name]
        
        self.feature_table['w_pred_mean'] = w_preds


        # Iterate through the input wp
        samples = self.feature_table['sample'].unique()
        weights = {sample:{} for sample in samples}
        for i in range(len(self.feature_table)):
            sample = self.feature_table.loc[i, 'sample']
            mode = self.feature_table.loc[i, 'mode']
            w_pred = self.feature_table.loc[i, 'w_pred_mean']
            weights[sample][mode] = w_pred

        print(self.feature_table)
        print(weights[sample])
        
        return