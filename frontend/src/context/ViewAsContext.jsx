import { createContext, useContext } from 'react'

/**
 * When an admin opens another user's library, this provides that user's id. Data hooks send it as
 * X-View-As and include it in their query keys, so cached data never mixes between libraries.
 * @typedef {{viewAsId: string|null, viewAsEmail: string|null, readOnly: boolean}} ViewAsValue
 */
const ViewAsContext = createContext(/** @type {ViewAsValue} */ ({ viewAsId: null, viewAsEmail: null, readOnly: false }))

export function ViewAsProvider({ userId, email, children }) {
  return (
    <ViewAsContext.Provider value={{ viewAsId: userId, viewAsEmail: email, readOnly: true }}>
      {children}
    </ViewAsContext.Provider>
  )
}

/** @returns {ViewAsValue} */
export function useViewAs() {
  return useContext(ViewAsContext)
}
