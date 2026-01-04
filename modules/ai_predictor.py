import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

class ProcurementAI:
    def __init__(self):
        self.model_moq = RandomForestRegressor(n_estimators=50, random_state=42)
        self.model_leadtime = RandomForestRegressor(n_estimators=50, random_state=42)
        self.is_trained = False

    def train_model(self):
        """Simulasi training model dengan data sintetik"""
        # Feature: [Cost Price, Is_Import (0/1), Stock]
        # Target: [MOQ, Leadtime]
        
        # Buat 500 data dummy untuk belajar pola
        np.random.seed(42)
        cost = np.random.uniform(10, 1000, 500)
        is_import = np.random.choice([0, 1], 500)
        stock = np.random.randint(0, 200, 500)
        
        X = pd.DataFrame({'cost': cost, 'is_import': is_import, 'stock': stock})
        
        # Logic Pattern: Import leadtime lama, Barang murah MOQ tinggi
        y_moq = (1000 / (cost + 1)) + (is_import * 50) 
        y_lt = 7 + (is_import * 60) + (stock * -0.1)
        
        self.model_moq.fit(X, y_moq)
        self.model_leadtime.fit(X, y_lt)
        self.is_trained = True

    def predict(self, cost_price, item_type_str, stock):
        if not self.is_trained:
            self.train_model()
            
        is_import = 1 if item_type_str == "Import" else 0
        features = pd.DataFrame([[cost_price, is_import, stock]], columns=['cost', 'is_import', 'stock'])
        
        pred_moq = self.model_moq.predict(features)[0]
        pred_lt = self.model_leadtime.predict(features)[0]
        
        # Post-processing agar angkanya cantik (bulatkan)
        final_moq = int(max(10, round(pred_moq, -1))) # Minimal 10, round puluhan
        final_lt = int(max(3, round(pred_lt)))        # Minimal 3 hari
        
        return final_moq, final_lt