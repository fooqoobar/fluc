// Basically generates a certain amount of numbers (like range in Python)
const range = ( start, end ) => Array.from( { length: end - start + 1 }, ( _, i ) => start + i );

const permissionBits = range(0, 50);
const permissionFlags = permissionBits.map( i => 1n << BigInt( i ) ).reduce( ( a, b ) => a | b, 0n );


function save( reset )
{
    const details = document.querySelectorAll( 'details[data]' );
    const data = { };

    details.forEach( detail =>
    {
        const type = detail.getAttribute( 'data' );
        const inputs = detail.querySelectorAll( 'input[data]' );
        data[ type ] = { };

        inputs.forEach( input =>
        {
            const key = input.getAttribute( 'data' );
            const value = input.type === 'checkbox' ? input.checked : input.value;

            if ( !data[ type ][ key ] )
            {
                data[ type ][ key ] = [ ];
            }

            if ( value )
            {
                data[ type ][ key ].push( value );
            }
        } );

    } );

    payload = {
        settings: data
    };

    if ( reset )
    {
        payload.reset = true;
    }
    
    fetch(
        '/settings',
        {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify( payload )
        }
    ).then( response =>
    {
        return new Promise( resolve => setTimeout( resolve, 200 ) );
    } ).then( ( ) => 
    {
        window.location.href = '/settings';
    } );
}


function addInput( event, inputlist, limit )
{
    if ( !inputlist )
    {
        return
    }

    const inputs = inputlist.getElementsByTagName( 'input' );
    const input = event.target;
    const inputType = input.type;
    const lastInput = inputs[ inputs.length - 1 ];
    const firstInput = inputs[ 0 ];
    
    function createInput( )
    {
        const newInput = document.createElement( 'input' );
        if ( inputType === 'checkbox' )
        {
            newInput.type = 'checkbox';
        }
        else
        {
            newInput.type = 'text';
        }

        for ( let attribute of lastInput.attributes )
        {
            if (
                ![ 'value', 'required' ].includes( attribute.name ) ||
                ( attribute.name === 'value' && inputs.length === 1 )
            )
            {
                newInput.setAttribute( attribute.name, attribute.value );
            }
        }

        newInput.addEventListener( 'input', event =>
        {
            addInput( event, inputlist, limit );
        } );

        inputlist.appendChild( newInput );
        return newInput;
    }
    
    if ( inputs.length < limit && inputType !== 'checkbox' )
    {
        if ( input.value.trim( ) !== '' )
        {
            createInput( );
        }
    }

    if ( inputType === 'checkbox' )
    {
        const checkedCount = Array.from(inputs).filter( input => input.checked ).length;
        const totalCount = inputs.length;
        
        // If we have one checkbox and it's checked, add a second unchecked one
        if ( totalCount === 1 && checkedCount === 1 )
        {
            createInput();
            return;
        }
        
        // If we have two checkboxes
        if ( totalCount === 2 )
        {
            const first = inputs[0];
            const second = inputs[1];
            
            // If second is checked, remove first
            if ( second.checked )
            {
                first.remove();
                return;
            }
            
            // If first is unchecked and second exists, remove second
            if ( !first.checked )
            {
                second.remove();
                return;
            }
        }
    }

    if (
        ( inputType !== 'checkbox' && input.value.trim( ) === '') &&
        inputs.length > 1
    )
    {
        input.remove( );
    }
}


function checkRegex( input, regex, message )
{
    input.addEventListener( 'input', ( ) =>
    {
        if ( !regex.test( input.value ) )
        {
            input.setCustomValidity( message );
            input.reportValidity( );
        }
        else
        {
            input.setCustomValidity( '' );
        }
    } );

    input.addEventListener( 'blur', ( ) =>
    {
        if ( !regex.test( input.value ) )
        {
            input.value = '';
            input.setCustomValidity( '' );
            input.reportValidity( );
        }
    } );
}


function addListeners( html )
{
    const inputList = html.querySelectorAll( '.input-list' );

    html.querySelectorAll( 'input' ).forEach( input => {
        input.addEventListener( 'input', ( ) => 
        {
            input.setAttribute( 'value', input.value );
        } );
    } );

    html.querySelectorAll( 'input[_maxlength], input[_minlength]' ).forEach( input =>
    {
        const maxLength = input.hasAttribute( '_maxlength' ) ? parseInt( input.getAttribute( '_maxlength' ), 10 ) : null;
        const minLength = input.hasAttribute( '_minlength' ) ? parseInt( input.getAttribute( '_minlength' ), 10 ) : null;
        
        input.addEventListener( 'input', ( ) =>
        {
            if ( maxLength !== null && input.value.length > maxLength )
            {
                input.setCustomValidity( `You have exceeded the maximum limit of ${maxLength} characters` );
                input.reportValidity( );
            }
            else if ( minLength !== null && input.value.length < minLength )
            {
                input.setCustomValidity( `A minimum of ${minLength} characters is required` );
                input.reportValidity( );
            }
            else
            {
                input.setCustomValidity( '' );
            }
        } );
            
        input.addEventListener( 'blur', ( ) =>
        {
            if ( maxLength !== null && input.value.length > maxLength )
            {
                input.value = input.value.slice( 0, maxLength );
            }
            else if ( minLength !== null && input.value.length < minLength )
            {
                input.value = '';
            }
            input.setCustomValidity( '' );
            input.reportValidity( );
        } );   
    } );


    html.querySelectorAll( 'input[check="emoji"]' ).forEach( input =>
    {
        const regex = /^[\p{Extended_Pictographic}\uFE0F]+$/u;
        checkRegex( input, regex, 'Please enter a valid emoji' )
    } );

    html.querySelectorAll( 'input[check="basic"]' ).forEach( input =>
    {
        const regex = /^[A-Za-z0-9_]+$/;
        checkRegex( input, regex, 'Please only use these characters: A-Z; a-z; 0-9; _' )
    } );

    html.querySelectorAll( 'input[check="url"]' ).forEach( input =>
    {
        const regex = /^https?:\/\/([-a-zA-Z0-9@:%._\+~#=]{1,256}\.)+[a-zA-Z]{2,6}([-a-zA-Z0-9@:%_\+.~#?&//=]*)$/;
        checkRegex( input, regex, 'Please enter a valid URL' );
    } );

    html.querySelectorAll( 'input[check="permissions"]' ).forEach( input =>
    {
        function isValid( value )
        {
            let valid = false;

            try
            {
                const _value = BigInt( value );
                valid = ( _value & ~permissionFlags ) === 0n;
            }
            catch { }
            return valid;
        }

        input.addEventListener( 'input', ( ) =>
        {
            if ( !isValid( input.value ) )
            {
                input.setCustomValidity( 'Invalid Discord permission flags' );
            }
            else
            {
                input.setCustomValidity( '' );
            }
        } );
        
        input.addEventListener( 'blur', ( ) =>
        {
            if ( !isValid( input.value ) )
            {
                input.value = '';
                input.setCustomValidity( '' );
                input.reportValidity( );
            }
        } );
    } );
    
    inputList.forEach( input =>
    {
        const inputs = input.querySelector( 'input' );
        inputs.addEventListener( 'input', event =>
        {
            addInput( event, input, 25 );
        } );
    } );
    
    html.querySelectorAll( '.checkbox-list' ).forEach( checkbox =>
    {
        const checkboxes = checkbox.querySelector( 'input' );
        checkboxes.addEventListener( 'input', event =>
        {
            addInput( event, checkbox, 2 );
        } );
    } );

    html.querySelectorAll( 'input[type="number"]', input =>
    {
        const max = input.getAttribute( 'max' );
        if ( max )
        {
            input.addEventListener( 'input', ( ) =>
            {
                if ( input.value > max )
                {
                    input.setCustomValidity( `The number should be smaller than ${max}` );
                }
                else
                {
                    input.setCustomValidity( '' );
                }
            } );
            
            input.addEventListener( 'blur', ( ) =>
            {
                if ( input.value > max )
                {
                    input.value = max;
                    input.setCustomValidity( '' );
                    input.reportValidity( );
                }
            } );
        }
    } );
}


document.getElementById( 'save' ).addEventListener( 'click', ( ) =>
{
    save( null );
} );

document.getElementById( 'reset' ).addEventListener( 'click', ( ) =>
{
    save( true );
} );

document.querySelectorAll( '.inputs details' ).forEach( detail =>
{
    const summary = detail.querySelector( 'summary' );
    const content = detail.querySelector( 'div' );

    summary.addEventListener( 'click', event => 
    {
        event.preventDefault( );
        const modal = document.createElement( 'div' );
        const modalContent = document.createElement( 'div' );
        const closeButton = document.createElement( 'span' );
        const cloned = content.cloneNode( true );

        modal.classList.add( 'modal' );
        modalContent.classList.add( 'modal-content' );
        closeButton.classList.add( 'modal-close' );
        closeButton.textContent = '×';

        modalContent.appendChild( closeButton );
        modalContent.appendChild( cloned );
        modal.appendChild( modalContent );
        
        document.body.appendChild( modal );
        document.body.classList.add( 'modal-open' );
        
        function closeModal( )
        {
            content.innerHTML = cloned.innerHTML;
            document.body.removeChild( modal );
            document.body.classList.remove( 'modal-open' );
        }

        closeButton.addEventListener( 'click', event =>
        {
            if ( event.target === closeButton )
            {
                closeModal( );
            }
        } );

        modal.addEventListener( 'click', event =>
        {
            if ( event.target === modal )
            {
                closeModal( );
            }
        } );

        addListeners( cloned );
    } );
} );


window.addEventListener( 'beforeunload', event =>
{
    event.preventDefault( );
    event.returnValue = '';
} );