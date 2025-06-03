const clock = document.getElementById( 'clock' );
        function updateClock( )
        {
            timestamp = clock.getAttribute( 'timestamp' );
            timestamp = parseInt( timestamp, 10 );

            if ( isNaN( timestamp ) )
            {
                return;
            }
            
            const date = new Date( timestamp );
            clock.textContent = date.toString( );

            setTimeout(( ) => {
                updateClock( );
            }, 1000)
        }
        updateClock( );