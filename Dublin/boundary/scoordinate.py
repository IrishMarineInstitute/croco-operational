import numpy as np

def scoord2z(point_type, zeta, topo, theta_s, theta_b, N, hc, scoord='new2008', Dcrit=0.2):
    '''
    scoord2z finds z at either rho or w points (positive up, zero at rest surface)

    Inputs:
      point_type        'r' or 'w'
      zeta               sea surface height
      topo              array of depths (e.g., from grd file)
      theta_s           surface focusing parameter
      theta_b           bottom focusing parameter
      N                 number of vertical rho-points
      hc                critical depth
      scoord            'new2008' :new scoord 2008  or 'old1994' for Song scoord
    
    Outputs:
      z                 depth
      Cs                Cs parameter
      sc                sigma coordinate
    '''
    def CSF(sc,theta_s,theta_b):
        '''
        Allows use of theta_b > 0 (July 2009)
        '''
        one64 = np.float64(1)
        if theta_s > 0.:
            csrf = ((one64-np.cosh(theta_s*sc))
                       /(np.cosh(theta_s)-one64))
        else:
            csrf = -sc**2
        sc1 = csrf+one64
        if theta_b > 0.:
            Cs = ((np.exp(theta_b*sc1)-one64)
                /(np.exp(theta_b)-one64)-one64)
        else:
            Cs = csrf
        return Cs

    N = np.float64(N)
    if isinstance(zeta,float):
        zeta = np.ones(topo.shape)*zeta
    if scoord not in 'new2008':
        cff1 = 1./np.sinh(theta_s)
        cff2 = 0.5/np.tanh(0.5*theta_s)
    sc_w = (np.arange(N+1,dtype=np.float64)-N)/N
    sc_r = ((np.arange(1,N+1,dtype=np.float64))-N-0.5)/N

    if 'w' in point_type:
        sc = sc_w
        N += 1. # add a level
    else:
        sc = sc_r
        
    if len(np.array(zeta).shape)>2: # case zeta is 3-D (in time)
        z  = np.empty((int(zeta.shape[0]),) + (int(N),) + topo.shape, dtype=np.float64)
    else:
        z  = np.empty((int(N),) + topo.shape, dtype=np.float64)

    if scoord in 'new2008':
        Cs = CSF(sc,theta_s,theta_b)
    elif scoord in 'old1994':
        Cs = (1.-theta_b)*cff1*np.sinh(theta_s*sc)+ \
           theta_b*(cff2*np.tanh(theta_s*(sc+0.5))-0.5)

    if scoord in 'new2008':
        hinv = 1. / (abs(topo) + hc)
        cff = hc * sc
        cff1 = Cs
            
        if len(np.array(zeta).shape)>2:
            for t in range(zeta.shape[0]):
                zeta[t][zeta[t]<(Dcrit-topo)] = Dcrit-topo[zeta[t]<(Dcrit-topo)]
                if 'w' in point_type:
                    z[t,0] = -topo
                    start = 1
                else:
                    start = 0
                for k in np.arange(start,N, dtype=int):
                    z[t,k] = zeta[t]+(zeta[t]+topo)* \
                             (cff[k]+cff1[k]*abs(topo))*hinv
        else:
            zeta[zeta<(Dcrit-topo)] = Dcrit-topo[zeta<(Dcrit-topo)]
            for k in np.arange(N, dtype=int):
                z[k] = zeta+(zeta+topo)* \
                       (cff[k]+cff1[k]*abs(topo))*hinv

    elif scoord in 'old1994':
        topo[topo==0] = 1.e-2
        hinv = 1./topo
        cff = hc*(sc-Cs)
        cff1 = Cs
        cff2 = sc + 1

        if len(np.array(zeta).shape)>2:
            for t in range(zeta.shape[0]):
                zeta[t][zeta[t]<(Dcrit-topo)] = Dcrit-topo[zeta[t]<(Dcrit-topo)]
                for k in np.arange(N,dtype=int) + 1:
                    z0 = cff[k-1]+cff1[k-1]*topo
                    z[t,k-1, :] = z0+zeta[t,:]*(1.+z0*hinv)
        else:
            zeta[zeta<(Dcrit-topo)] = Dcrit-topo[zeta<(Dcrit-topo)]
            for k in np.arange(N,dtype=int) + 1:
                z0 = cff[k-1]+cff1[k-1]*topo
                z[k-1, :] = z0+zeta*(1.+z0*hinv)
    else:
        raise Exception("Unknown scoord, should be 'new2008' or 'old1994'")

    if sc_r is None:
        sc_r = sc_r
    return z.squeeze(), np.float32(Cs), sc
