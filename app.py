
"""
Check frame rate in Maya

"""

import sys
import os

from tank.platform import Application
from tank.platform.qt import QtCore, QtGui
import tank
import pymel.core as pm
import maya.cmds as cmds


class mayaFpsCheck(Application):

    def init_app(self):
        """
        App entry point
        """
        self.log_debug("start maya fps check app")
        self.mayaFpsDict = self.get_setting("maya_fps_list")

        self.FpsSceneOpened() # run the method when the app is started
        self.job = cmds.scriptJob( event=["SceneOpened", self.FpsSceneOpened], protected=True ) # will run if a scene (new or not) is opened
        self.log_debug("Creating protected scriptJobs %s " % self.job)


    @property
    def context_change_allowed(self):
        """
        Specifies that context changes are allowed.
        """
        return True

    def destroy_app(self):
        """
        App teardown
        """
        self.log_debug("Destroying maya check fps app, killing scriptJob %s" % self.job)
        cmds.scriptJob( kill=self.job, force=True)



    ###############################################################################################
    # implementation


    def FpsSceneOpened(self):
        '''
        compare maya scene fps and shotgun project fps. If the maya scene is new/empty set it's framerate to the shotgun project fps without
        asking the user. If scene is not new (has already objects) warn the user and give him the choice
        to either leave the maya scene fps unchanged or to change it to the shotgun project fps.
        '''

        mayaSceneFpsName = self.getMayaSceneFps()
        mayaSceneFps = self.convertMayaFpsToShotgunFps(mayaSceneFpsName)
        shotgunProjectFps = self.getShotgunProjectFps()
        undefinedShotgunProjectFps = False

        if shotgunProjectFps is None: # if the sg_projectfps field has been left blank
            undefinedShotgunProjectFps = True
            shotgunProjectFps = 25.0 # force it to 25
            self.log_debug("FpsSceneOpened : Shotgun project fps is not defined, assuming it should be 25.0")
        newfps = self.convertShotgunFpsToMayaFps(shotgunProjectFps)

        defaultNodes = ['lambert1', 'particleCloud1', 'persp', 'perspShape', 'top', 'topShape', 'front', 'frontShape', 'side', 'sideShape']
        sceneNodes = cmds.ls(materials = True, dag = True)

        if sceneNodes == defaultNodes: # in this case, we are dealing with a new scene (not a perfect solution, but I don't see another way to check)
            cmds.currentUnit( time=newfps, updateAnimation=False )
            self.log_debug("New Maya scene fps was %s, changing it silently to %s fps" % (mayaSceneFpsName, shotgunProjectFps))

        else: # it's not an new empty scene
            if mayaSceneFps != shotgunProjectFps:
                if not undefinedShotgunProjectFps:
                    msg = "Maya scene frame rate is %s fps ('%s'). Shotgun project is set to %s fps.\nChange frame rate to %s fps ?" % (mayaSceneFps, mayaSceneFpsName, shotgunProjectFps, shotgunProjectFps)
                elif undefinedShotgunProjectFps:
                    msg = "Maya scene frame rate is %s fps ('%s'). Shotgun project frame rate is undefined.\nIt should probably be 25 fps. Change frame rate to 25 fps ?" % (mayaSceneFps, mayaSceneFpsName)
                
                change = "Change to %s fps" % shotgunProjectFps
                cancel = "Leave at %s fps ('%s')" % (mayaSceneFps, mayaSceneFpsName)
                
                userResponse = cmds.confirmDialog(title='Frame Rate Warning', message=msg, button=[change, cancel], defaultButton=change, cancelButton=cancel)
                
                if userResponse == change:
                    cmds.currentUnit( time=newfps, updateAnimation=False )
                    self.log_debug("FpsSceneOpened : Maya scene fps was %s, changing it to %s fps" % (mayaSceneFpsName, shotgunProjectFps))

    


    ########################## internal methods

    def reverseDict(self, d):

        d2 = {}
        for k,v in d.items():
            if v in d2.keys():
                raise KeyError('Cannot create bidirectional dict. ' +
                               'Either d has a value that is the same as one of ' +
                               'its keys or multiple keys have the same value.')
            d2[v] = k
        return d2

    def convertMayaFpsToShotgunFps(self, fps):

        return self.mayaFpsDict[fps]

    def convertShotgunFpsToMayaFps(self, fps):

        shotgunFpsDict = self.reverseDict(self.mayaFpsDict)
        return shotgunFpsDict[fps]

    def getMayaSceneFps(self):
        return cmds.currentUnit( query=True, time=True )

    def getShotgunProjectFps(self):

        tk = self.sgtk
        ctx = self.context
        project = ctx.project
        sg_filters = [['id', 'is', project['id']]]
        fields = ["sg_projectfps"]
        data = tk.shotgun.find_one('Project', filters=sg_filters, fields=fields)
        try:
            shotgunProjectFps = data['sg_projectfps'] # this returns none if left unspecified, otherwise returns a float
            
        except: # if there's no sg_projectfps field
            shotgunProjectFps = None

        return shotgunProjectFps