
"""
Check frame rate in Maya. This replaces and hopefully improves the fpsWatcher mel script
This fpsWatcher script is located in :
//vapps/apps/Maya/sharedScripts/sourcedScripts/utils

The fpsWatcher script is called from the userSetup.mel that resides in :
//vapps/apps/Maya/sharedScripts/userSetup.mel, line 252.


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
        self.log_debug("Creating protected scriptJob %s " % self.job)


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
        if cmds.scriptJob( exists=self.job ): 
            cmds.scriptJob( kill=self.job, force=True)
            self.log_debug("Destroying maya check fps app, killing scriptJob %s" % self.job)
        else: self.log_debug("Tried to delete scriptJob %s of tk-maya-fps but job does not exist anymore" % self.job)



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
        if mayaSceneFps is None:
            warning = "Maya scene frame rate is: '%s'. Could not translate this to a fps value.\nPlease adapt the app configuration in shotgun's env files" % mayaSceneFpsName
            warnDialog = cmds.confirmDialog(title='Frame Rate Warning', message=warning, button=['ok'])
            self.log_debug("Maya scene frame rate is: '%s'. Could not translate this to a fps value. Please adapt the app configuration in shotgun's env files" % mayaSceneFpsName)
            return
        shotgunProjectFps = self.getShotgunProjectFps()
        undefinedShotgunProjectFps = False

        if shotgunProjectFps is None: # if the sg_projectfps field has been left blank
            undefinedShotgunProjectFps = True
            shotgunProjectFps = 25.0 # force it to 25
            self.log_debug("FpsSceneOpened : Shotgun project fps is not defined, assuming it should be 25.0")
            
        newMayaFps = self.convertShotgunFpsToMayaFps(shotgunProjectFps)
        if newMayaFps is None:
            self.log_debug('Shotgun project is set to %s fps. Could not find the corresponding Maya frame rate' % shotgunProjectFps )
            warning = "Shotgun project is set to %s fps. Could not find the corresponding Maya frame rate.\nPlease adapt the app configuration in shotgun's env files" % shotgunProjectFps
            warnDialog = cmds.confirmDialog(title='Frame Rate Warning', message=warning, button=['ok'])
            return


        # for Maya versions > 2019, default nodes in empty scene are:
        defaultNodes = ['lambert1', 'standardSurface1', 'particleCloud1', 'persp', 'perspShape', 'top', 'topShape', 'front', 'frontShape', 'side', 'sideShape']

        sceneNodes = cmds.ls(materials = True, dag = True)

        if sceneNodes == defaultNodes: # in this case, we are dealing with a new scene (not a perfect solution, but I don't see another way to check)
            if mayaSceneFps != shotgunProjectFps:
                cmds.currentUnit( time=newMayaFps, updateAnimation=False )

                # Change the in and out values to round values
                animationStart = cmds.playbackOptions( q=True, animationStartTime=True )
                animationEnd = cmds.playbackOptions( q=True, animationEndTime=True )
                minTime = cmds.playbackOptions( q=True, minTime=True )
                maxTime = cmds.playbackOptions( q=True, maxTime=True )
                curtime = cmds.currentTime( q= True )

                cmds.playbackOptions( 
                    animationStartTime = int(round(animationStart)),
                    animationEndTime = int(round(animationEnd)),
                    minTime = int(round(minTime)),
                    maxTime = int(round(maxTime))
                        )
                cmds.currentTime( int(round(curtime)) )

                self.log_debug("New Maya scene fps was: '%s', changing it silently to %s fps to match this shotgun project's fps value" % (mayaSceneFpsName, shotgunProjectFps))

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
                    cmds.currentUnit( time=newMayaFps, updateAnimation=False )
                    # Change the in and out values to round values
                    animationStart = cmds.playbackOptions( q=True, animationStartTime=True )
                    animationEnd = cmds.playbackOptions( q=True, animationEndTime=True )
                    minTime = cmds.playbackOptions( q=True, minTime=True )
                    maxTime = cmds.playbackOptions( q=True, maxTime=True )
                    curtime = cmds.currentTime( q= True )

                    cmds.playbackOptions( 
                        animationStartTime = int(round(animationStart)),
                        animationEndTime = int(round(animationEnd)),
                        minTime = int(round(minTime)),
                        maxTime = int(round(maxTime))
                            )
                    cmds.currentTime( int(round(curtime)) )
                    self.log_debug("FpsSceneOpened : Maya scene fps was: '%s', changing it to %s fps" % (mayaSceneFpsName, shotgunProjectFps))

    


    ########################## internal methods


    def convertMayaFpsToShotgunFps(self, fps):

        if fps in self.mayaFpsDict:
            return self.mayaFpsDict[fps]
        else : return None


    def convertShotgunFpsToMayaFps(self, fps):

        for mayaFpsName, shotgunFps in self.mayaFpsDict.items():
            if shotgunFps == fps:
                return mayaFpsName
        return None


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