#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.rad_bio.py
"""
Class to view and calculate Random Forest
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
# from threading import Thread
# from pubsub import pub
from dvha.dialogs.export import save_data_to_file
from dvha.tools.machine_learning import get_random_forest
from dvha.models.plot import PlotRandomForest
from dvha.tools.utilities import set_msw_background_color, get_window_size


class RandomForestFrame(wx.Frame):
    """
    View random forest predictions for provided data
    """
    def __init__(self, X, y, x_variables, y_variable, multi_var_pred, multi_var_mse, options, mrn, study_date, uid,
                 regressor=get_random_forest, title='Random Forest'):
        """
        :param X:
        :param y: data to be modeled
        :type y: list
        :param x_variables:
        :param y_variable:
        :param options: user options
        :type options: Options
        """
        wx.Frame.__init__(self, None)

        set_msw_background_color(self)  # If windows, change the background color

        self.X, self.y = X, y
        self.x_variables, self.y_variable, self.uid = x_variables, y_variable, uid

        self.regressor = regressor
        self.title = title

        self.plot = PlotRandomForest(self, options, X, y, multi_var_pred, mrn, study_date, multi_var_mse)

        self.SetSize(get_window_size(0.595, 0.714))
        self.spin_ctrl_trees = wx.SpinCtrl(self, wx.ID_ANY, "100", min=1, max=1000)
        init_features = [1, 2][len(x_variables) > 1]
        self.spin_ctrl_features = wx.SpinCtrl(self, wx.ID_ANY, str(init_features), min=1, max=len(x_variables))
        self.button_calculate = wx.Button(self, wx.ID_ANY, "Calculate")
        self.button_save_plot = wx.Button(self, wx.ID_ANY, "Save Plot")
        self.button_export = wx.Button(self, wx.ID_ANY, "Export Data")

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.Show()

        self.on_update(None)

    def __set_properties(self):
        self.SetTitle(self.title)
        self.spin_ctrl_trees.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                             wx.FONTWEIGHT_NORMAL, 0, ".SF NS Text"))
        self.spin_ctrl_trees.SetToolTip("n_estimators")
        self.spin_ctrl_features.SetToolTip("Maximum number of features when splitting")

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_update, id=self.button_calculate.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_save_plot.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_export.GetId())
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_input_and_plot = wx.BoxSizer(wx.VERTICAL)
        sizer_hyper_parameters = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Hyper-parameters:"), wx.HORIZONTAL)
        sizer_features = wx.BoxSizer(wx.HORIZONTAL)
        sizer_trees = wx.BoxSizer(wx.HORIZONTAL)

        label_trees = wx.StaticText(self, wx.ID_ANY, "Number of trees:")
        sizer_trees.Add(label_trees, 0, wx.ALL, 5)
        sizer_trees.Add(self.spin_ctrl_trees, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(sizer_trees, 1, wx.EXPAND, 0)

        label_features = wx.StaticText(self, wx.ID_ANY, "Max feature count:")
        sizer_features.Add(label_features, 0, wx.ALL, 5)
        sizer_features.Add(self.spin_ctrl_features, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(sizer_features, 1, wx.EXPAND, 0)

        sizer_hyper_parameters.Add(self.button_calculate, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(self.button_save_plot, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(self.button_export, 0, wx.ALL, 5)

        sizer_input_and_plot.Add(sizer_hyper_parameters, 0, wx.EXPAND, 0)

        sizer_input_and_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_input_and_plot, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Center()
        self.Layout()

    def on_update(self, evt):
        y_pred, mse, importance = self.regressor(self.X, self.y, n_estimators=self.spin_ctrl_trees.GetValue(),
                                                 max_features=self.spin_ctrl_features.GetValue())
        self.plot.update_data(y_pred, importance, self.x_variables, self.y_variable, mse, self.uid)

    def redraw_plot(self):
        self.plot.redraw_plot()

    def on_resize(self, *evt):
        try:
            self.Refresh()
            self.Layout()
            wx.CallAfter(self.redraw_plot)
        except RuntimeError:
            pass

    def on_export(self, evt):
        save_data_to_file(self, 'Save random forest data to csv', self.plot.get_csv())

    def on_save_plot(self, evt):
        save_data_to_file(self, 'Save random forest plot', self.plot.html_str,
                          wildcard="HTML files (*.html)|*.html")


# class RandomForestWorker(Thread):
#     """
#     Thread to calculate random forest apart
#     """
#     def __init__(self, X, y, n_estimators=None, max_features=None):
#         """
#         :param X: independent data matrix
#         :type X: numpy.array
#         :param y: numpy.array
#         :param n_estimators:
#         :param max_features:
#         """
#         Thread.__init__(self)
#         self.X, self.y = X, y
#
#         self.kwargs = {}
#         if n_estimators is not None:
#             self.kwargs['n_estimators'] = n_estimators
#         if max_features is not None:
#             self.kwargs['max_features'] = max_features
#         self.start()  # start the thread
#
#     def run(self):
#         y_predict, mse = get_random_forest(self.X, self.y, **self.kwargs)
#         msg = {'y_predict': y_predict, 'mse': mse}
#         wx.CallAfter(pub.sendMessage, "random_forest_complete", msg=msg)
