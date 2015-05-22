# Odyo
Moteur audio utilisant Gstreamer

INSTALLATION
============
make install

UNINSTALLATION
==============
make uninstall

UTILISATION
===========
#USAGE:

    play            New player
    
        odyo play "/realpath/filename" <fadein> <fadeout>
        
        
    pause           Pause player
    
        odyo pause
        
        
    stop            Stop player
    
        odyo stop
        
        
    seek            Seek in player
    
        odyo seek <milliseconds>
        
        
    volume          Set volume player
    
        odyo volume <0-100>
        
        
    filename            Current filename
    
        odyo filename
        
            return: "/realpath/filename"
            
        
    position        Display current position
    
        odyo position 
        
            return: <position>

