from scipy.fft import fft
import numpy as np

def initialize_loss_weighting(X_r, y_r):
    N_modes = X_r.shape[0]
    w = np.ones(N_modes) * 0.5
    y_pred = np.matmul(w, X_r)
    e_fft_0 = fft_loss(y_r, y_pred)
    e_std_0 = std_loss(y_r, y_pred)
    e_min_0 = min_loss(y_r, y_pred)
    e_max_0 = max_loss(y_r, y_pred)
    e_hist_0 = hist_loss(y_r, y_pred)
    return e_fft_0, e_std_0, e_min_0, e_max_0, e_hist_0

def fft_loss(y, y_pred):
    fft_y = fft(y)
    fft_y_pred = fft(y_pred)
    
    # Find the distance between the two vectors 
    loss = np.linalg.norm(fft_y - fft_y_pred)
    return loss

def std_loss(y, y_pred):
    std_true = y.std()
    std_pred = y_pred.std()
    return np.abs(std_true-std_pred)

def max_loss(y, y_pred):
    true_max = y.max()
    pred_max = y_pred.max()
    error = np.abs(true_max - pred_max)
    return error

def min_loss(y, y_pred):
    true_min = y.min()
    pred_min = y_pred.min()
    error = np.abs(true_min - pred_min)
    return error

def hist_loss(y, y_pred):
    bins = np.linspace(-0.1, 0.1, 29)
    h, b = np.histogram(y, bins=bins)
    h_pred, b = np.histogram(y_pred, bins=bins)
    return np.linalg.norm(h-h_pred)
