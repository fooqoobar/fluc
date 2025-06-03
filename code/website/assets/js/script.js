const is_mobile = /Mobi|Android|iPhone|iPad|iPod|Windows Phone/i.test( navigator.userAgent );
let last_touch;


document.addEventListener( 'contextmenu', event =>
{
    event.preventDefault( );
} );


if ( is_mobile )
{
    document.addEventListener( 'touchstart', event =>
    {
        let time = new Date().getTime();
        if ( time - last_touch <= 300 )
        {
            event.preventDefault();
        }
        last_touch = time;
    },
    {
        passive: false
    } );
}

`
⠀⠀⠀⠀⠀⠀⠀⠀⣠⣶⣿⣿⣿⣷⣤⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣾⡿⠋⠀⠿⠇⠉⠻⣿⣄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢠⣿⠏⠀⠀⠀⠀⠀⠀⠀⠙⣿⣆⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢠⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣆⠀⠀⠀⠀
⠀⠀⠀⠀⢸⣿⡄⠀⠀⠀⢀⣤⣀⠀⠀⠀⠀⣿⡿⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠻⣿⣶⣶⣾⡿⠟⢿⣷⣶⣶⣿⡟⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡏⠉⠁⠀⠀⠀⠀⠉⠉⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⣸⣿⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣿⡇⢀⣴⣿⠇⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⢀⣠⣴⣿⣷⣿⠟⠁⠀⠀⠀⠀⠀⣿⣧⣄⡀⠀⠀⠀
⠀⢀⣴⡿⠛⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠙⢿⣷⣄⠀
⢠⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣆
⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿
⣿⣇⠀⠀⠀⠀⠀⠀⢸⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿
⢹⣿⡄⠀⠀⠀⠀⠀⠀⢿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⡿
⠀⠻⣿⣦⣀⠀⠀⠀⠀⠈⣿⣷⣄⡀⠀⠀⠀⠀⣀⣤⣾⡟⠁
⠀⠀⠈⠛⠿⣿⣷⣶⣾⡿⠿⠛⠻⢿⣿⣶⣾⣿⠿⠛⠉⠀⠀
`


document.addEventListener( 'DOMContentLoaded', ( ) =>
{
    const closeButtons = document.querySelectorAll( '.message-close' );
    const messages = document.querySelectorAll( '.success-message, .error-message' );
    
    messages.forEach( ( message ) => {
        message.addEventListener( 'transitionend', ( ) =>
        {
            message.remove( );
        } );

        setTimeout( ( ) => {
            message.classList.add( 'hidden' );
        }, 15000 );
    });

    closeButtons.forEach( button =>
    {
        button.addEventListener( 'click', event =>
        {
            if ( !event.target )
            {
                return
            }
            
            const message = event.target.closest( '.success-message, .error-message' );
            message.classList.add( 'hidden' );
        } );
    } );
} );


document.querySelectorAll( '.card' ).forEach( card =>
{
    if( !is_mobile )
    {
        card.addEventListener( 'mousemove', event =>
        {
            const rect = card.getBoundingClientRect( );
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
    
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
    
            const rotateX = ( y - centerY ) / 20;
            const rotateY = ( centerX - x ) / 20;
    
            card.style.transition = 'transform 0.2s ease';
            card.style.transform = `perspective(1000px) translate(-50%, -50%) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        } );
    
        card.addEventListener( 'mouseleave', ( ) =>
        {
            card.style.transition = 'transform 0.5s ease';
            card.style.transform = 'perspective(1000px) translate(-50%, -50%) rotateX(0) rotateY(0)';
        } );
    }
} );


// And you are still here..
document.addEventListener( 'keydown', event =>
{
    if (
        event.key === 'F12' || 
        ( event.ctrlKey && event.shiftKey && [ 'I', 'J', 'C' ].includes( event.key )) || 
        ( event.ctrlKey && ['U', 'S'].includes( event.key ) )
    )
    {
        event.preventDefault( );
    }
});