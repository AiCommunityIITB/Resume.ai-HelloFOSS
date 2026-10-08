import React from 'react'

const Navbar = () => {
  return (
    <nav className='fixed w-full flex m-10 px-10 justify-between'>
        <div>
             AI Community
        </div>
        <div className='flex justify-between px-20 '>
            <div className='mx-10'> Sign In</div>
            <div className='mx-10'> About</div>
            <div className='mx-10'> AI Model</div>
            <div className='mx-10'> Contacts </div>
        </div>
    </nav>
  )
}

export default Navbar